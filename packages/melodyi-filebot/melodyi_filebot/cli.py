"""CLI 命令行入口

子命令：search / fetch-summary / build-plan / execute-plan / undo
"""

from __future__ import annotations

import json
import logging

import click

from melodyi_filebot import __version__, config, tmdb
from melodyi_filebot.planner import build_plan_tv, build_plan_movie
from melodyi_filebot import fsops

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
@click.option("--show-id", type=int, required=False, help="TMDB 剧 ID")
@click.option("--movie-id", type=int, required=False, help="TMDB 电影 ID")
@click.option("--source", required=True, help="源目录")
@click.option("--dest", required=True, help="目标根目录")
@click.option("--language", "-l", default="zh-CN")
@click.option("--out", type=click.Path(), default=None, help="计划输出文件路径")
def build_plan(show_id, movie_id, source, dest, language, out):
    """构建重命名与目录整理计划"""
    logger.info("build-plan: show_id=%s movie_id=%s", show_id, movie_id)
    if bool(show_id) == bool(movie_id):
        raise click.UsageError("必须且只能指定 --show-id 或 --movie-id 之一")
    files = fsops.scan_video_files(source)
    if show_id:
        show = tmdb.get_show_summary(show_id, language=language)
        result = build_plan_tv(files, show, dest, language=language)
    else:
        from melodyi_filebot.models import CandidateSummary
        movie = tmdb.get_movie_summary(movie_id, language=language)
        result = build_plan_movie(files, movie, dest)
    output = result.model_dump()
    click.echo(json.dumps(output, ensure_ascii=False, indent=2))
    if out:
        import pathlib
        pathlib.Path(out).write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")


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
    import pathlib
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
