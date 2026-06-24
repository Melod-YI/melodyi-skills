"""CLI 命令行入口

子命令：search / fetch-summary / build-plan / execute-plan / undo
"""

from __future__ import annotations

import json
import logging
import pathlib

import click

from melodyi_filebot import __version__, config, tmdb
from melodyi_filebot.planner import (
    build_plan_tv, build_plan_movie,
    build_plan_tv_from_map, build_plan_movie_from_map,
    draft_map_tv,
)
from melodyi_filebot import fsops
from melodyi_filebot.models import PlanMap

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


@click.group()
@click.version_option(version=__version__, prog_name="melodyi-filebot")
def cli():
    """melodyi-filebot: 基于 TMDB 的影视批量重命名与目录整理工具"""
    pass


@cli.command()
@click.argument("query", metavar="query")
@click.option("--type", "media_type", type=click.Choice(["tv", "movie", "multi"]), default="tv")
@click.option("--language", "-l", default="zh-CN", help="语言 (默认 zh-CN)")
@click.option("--year", type=int, default=None, help="年份过滤")
def search(query, media_type, language, year):
    """搜索 TMDB"""
    logger.info("search: query=%r type=%s", query, media_type)
    cands = tmdb.search(query, media_type=media_type, language=language, year=year)
    if not cands:
        click.echo("未找到匹配结果。")
        return
    for c in cands:
        click.echo(f"[{c.media_type}] tmdb_id={c.tmdb_id} | {c.title} ({c.year}) | "
                   f"original={c.original_title} | overview_len={c.overview_length}")


@cli.command(name="fetch-summary")
@click.argument("tmdb_id", type=int)
@click.option("--language", "-l", default="zh-CN")
@click.option("--episodes", type=int, default=None, help="展开某季的集列表")
def fetch_summary(tmdb_id, language, episodes):
    """获取剧摘要（不含完整 overview）"""
    logger.info("fetch-summary: id=%s", tmdb_id)
    s = tmdb.get_show_summary(tmdb_id, language=language)
    click.echo(f"tmdb_id={s.tmdb_id} | {s.title} ({s.year}) | original={s.original_title}")
    click.echo(f"季数={s.total_seasons} 总集数={s.total_episodes} "
               f"overview_available={s.overview_available} overview_length={s.overview_length}")
    for season in s.seasons:
        click.echo(f"  S{season.season_number:02d} {season.name} | 集数={season.episode_count} "
                   f"overview_available={season.overview_available}")
    if s.episode_groups:
        click.echo("剧集组:")
        for g in s.episode_groups:
            click.echo(f"  group_id={g.id} | {g.name} | type={g.type}")
    if episodes is not None:
        eps = tmdb.get_season_episodes(tmdb_id, episodes, language=language)
        click.echo(f"第 {episodes} 季集列表:")
        for e in eps:
            click.echo(f"  E{e.episode_number:02d} {e.name} | overview_len={e.overview_length}")


@cli.command(name="build-plan")
@click.option("--show-id", type=int, required=False, help="TMDB 剧 ID（自动模式）")
@click.option("--movie-id", type=int, required=False, help="TMDB 电影 ID（自动模式）")
@click.option("--source", required=False, help="源目录（自动模式，扫描后按文件名解析）")
@click.option("--dest", required=True, help="目标根目录")
@click.option("--language", "-l", default="zh-CN")
@click.option("--season", type=int, default=None, help="季提示（自动模式）：文件名未带季标记时按此季号归类。文件名有显式季标记仍以文件名为准")
@click.option("--map", "map_path", type=click.Path(exists=True), default=None, help="显式映射文件（override 模式）：按映射构建，不解析文件名。与 --source/--show-id/--movie-id 互斥")
@click.option("--out", type=click.Path(), default=None, help="计划输出文件路径")
def build_plan(show_id, movie_id, source, dest, language, season, map_path, out):
    """构建重命名与目录整理计划

    两种模式：
    - 自动：--show-id/--movie-id + --source，按文件名解析季/集（可用 --season 提示季号）
    - override：--map <映射文件>，按显式映射构建（不解析文件名），映射可由 draft-map 生成初版后编辑
    """
    logger.info("build-plan: map=%s show_id=%s movie_id=%s source=%s", map_path, show_id, movie_id, source)

    if map_path:
        # override 模式：显式映射，禁止与自动模式参数混用
        if source or show_id or movie_id or season is not None:
            raise click.UsageError("--map 与 --source/--show-id/--movie-id/--season 互斥")
        plan_map = PlanMap.model_validate_json(
            pathlib.Path(map_path).read_text(encoding="utf-8")
        )
        if plan_map.media_type == "tv":
            show = tmdb.get_show_summary(plan_map.tmdb_id, language=plan_map.language or language)
            result = build_plan_tv_from_map(plan_map, show, dest)
        else:
            movie = tmdb.get_movie_summary(plan_map.tmdb_id, language=plan_map.language or language)
            result = build_plan_movie_from_map(plan_map, movie, dest)
    else:
        # 自动模式
        if not source:
            raise click.UsageError("自动模式需要 --source（或使用 --map 进入 override 模式）")
        if bool(show_id) == bool(movie_id):
            raise click.UsageError("必须且只能指定 --show-id 或 --movie-id 之一")
        if season is not None and not show_id:
            raise click.UsageError("--season 仅适用于剧集（--show-id）")
        files = fsops.scan_video_files(source)
        if show_id:
            show = tmdb.get_show_summary(show_id, language=language)
            result = build_plan_tv(files, show, dest, language=language, season_hint=season)
        else:
            movie = tmdb.get_movie_summary(movie_id, language=language)
            result = build_plan_movie(files, movie, dest)

    output = result.model_dump()
    click.echo(json.dumps(output, ensure_ascii=False, indent=2))
    if out:
            pathlib.Path(out).write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")


@cli.command(name="draft-map")
@click.option("--show-id", type=int, required=False, help="TMDB 剧 ID")
@click.option("--movie-id", type=int, required=False, help="TMDB 电影 ID")
@click.option("--source", required=True, help="源目录")
@click.option("--language", "-l", default="zh-CN")
@click.option("--season", type=int, default=None, help="季提示：文件名未带季标记时填入此季号（仅剧集）")
@click.option("--out", required=True, type=click.Path(), help="映射输出文件路径")
def draft_map(show_id, movie_id, source, language, season, out):
    """生成文件→季/集 映射初版（供编辑后交给 build-plan --map）

    扫描+解析文件名，输出猜测映射。不调用 TMDB，仅透传 tmdb_id。
    无法解析的文件 season/episode 为 None，由 agent 对照 fetch-summary 后补全。
    """
    logger.info("draft-map: show_id=%s movie_id=%s source=%s", show_id, movie_id, source)
    if bool(show_id) == bool(movie_id):
        raise click.UsageError("必须且只能指定 --show-id 或 --movie-id 之一")
    if season is not None and not show_id:
        raise click.UsageError("--season 仅适用于剧集（--show-id）")
    files = fsops.scan_video_files(source)
    if show_id:
        plan_map = draft_map_tv(files, tmdb_id=show_id, season_hint=season, language=language)
    else:
        from melodyi_filebot.models import FileMapping, PlanMap as _PM
        plan_map = _PM(
            media_type="movie", tmdb_id=movie_id, language=language,
            mappings=[FileMapping(file=f) for f in files],
        )
    output = plan_map.model_dump_json(indent=2, ensure_ascii=False)
    pathlib.Path(out).write_text(output, encoding="utf-8")
    click.echo(f"映射初版已写入: {out}（共 {len(plan_map.mappings)} 项）")
    click.echo("编辑后执行: melodyi-filebot build-plan --map " + out + " --dest <目标根目录>")


@cli.command(name="execute-plan")
@click.option("--plan", "plan_path", required=True, type=click.Path(exists=True))
@click.option("--execute", is_flag=True, help="真正执行（默认 dry-run）")
@click.option("--snapshot", type=click.Path(), default=None, help="事务日志保存路径（默认存到 ~/.melodyi-filebot/snapshots/ 下）")
def execute_plan_cmd(plan_path, execute, snapshot):
    """执行计划（默认 dry-run）

    真正执行（--execute）时一定会写事务日志，以便事后 undo：
    - 显式 --snapshot：写到指定路径
    - 未指定：默认写到 ~/.melodyi-filebot/snapshots/<plan文件名>.snapshot.json
    dry-run 不执行，不写日志。
    """
    plan_data = json.loads(pathlib.Path(plan_path).read_text(encoding="utf-8"))
    from melodyi_filebot.models import BuildPlanResult
    plan = BuildPlanResult(**plan_data)

    if execute and not snapshot:
        # 默认 snapshot 路径：plan 文件名（去扩展名）+ .snapshot.json
        plan_stem = pathlib.Path(plan_path).stem
        snapshots_dir = config.SNAPSHOTS_DIR
        snapshots_dir.mkdir(parents=True, exist_ok=True)
        snapshot = str(snapshots_dir / f"{plan_stem}.snapshot.json")
        logger.info("未指定 --snapshot，使用默认路径: %s", snapshot)

    snap = fsops.execute_plan(plan, dry_run=not execute, snapshot_path=snapshot if execute else None)
    if not execute:
        click.echo("dry-run 校验通过，未执行任何操作。加 --execute 真正执行。")
    else:
        click.echo("执行完成。")
        if snap and snapshot:
            click.echo(f"事务日志已保存: {snapshot}")
            click.echo(f"如需回滚，执行: melodyi-filebot undo \"{snapshot}\"")


@cli.command()
@click.argument("snapshot", type=click.Path(exists=True))
def undo(snapshot):
    """从事务日志回滚"""
    fsops.undo_from_file(snapshot)
    click.echo("回滚完成。")


if __name__ == "__main__":
    cli()
