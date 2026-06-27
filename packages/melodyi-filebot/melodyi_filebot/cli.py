"""CLI 命令行入口

子命令：search / fetch-summary / build-plan / execute-plan / undo
        bangumi-search / bangumi-subject / bangumi-episodes

日志风格参考 melodyi-web：默认静默（仅 ERROR），加 --verbose/-v 才输出 INFO 日志；
网络/API错误用 click.echo(err=True) + sys.exit(1) 友好报错，非 traceback。
"""

from __future__ import annotations

import json
import logging
import pathlib
import sys

import click
import httpx

from melodyi_filebot import __version__, config, tmdb, bangumi
from melodyi_filebot.structure import analyze_path, render_text
from melodyi_filebot.planner import (
    build_plan_tv, build_plan_movie,
    build_plan_tv_from_map, build_plan_movie_from_map,
    draft_map_tv,
)
from melodyi_filebot import fsops
from melodyi_filebot.models import PlanMap

logger = logging.getLogger(__name__)


def _configure_logging(verbose: bool) -> None:
    """配置日志：默认仅 ERROR（静默），--verbose 输出 INFO 级日志

    每次调用重建 handler 并绑定到当前 sys.stderr（CliRunner 等会替换 sys.stderr，
    若在 import 时建 handler 会绑到真实 stderr 而无法被捕获）。
    """
    level = logging.INFO if verbose else logging.ERROR
    root = logging.getLogger()
    root.handlers.clear()
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    )
    root.addHandler(handler)
    root.setLevel(level)


def _report_error(e: Exception) -> None:
    """友好报错（非 traceback）并以退出码 1 退出"""
    click.echo(f"错误: {e}", err=True)
    sys.exit(1)


@click.group()
@click.version_option(version=__version__, prog_name="melodyi-filebot")
@click.option("--verbose", "-v", is_flag=True, help="输出详细日志（默认仅输出错误）")
def cli(verbose):
    """melodyi-filebot: 基于 TMDB 的影视批量重命名与目录整理工具"""
    _configure_logging(verbose)


@cli.command()
@click.argument("query", metavar="query")
@click.option("--type", "media_type", type=click.Choice(["tv", "movie", "multi"]), default="tv")
@click.option("--language", "-l", default="zh-CN", help="语言 (默认 zh-CN)")
@click.option("--year", type=int, default=None, help="年份过滤")
def search(query, media_type, language, year):
    """搜索 TMDB"""
    logger.info("search: query=%r type=%s", query, media_type)
    try:
        cands = tmdb.search(query, media_type=media_type, language=language, year=year)
    except (RuntimeError, httpx.HTTPError) as e:
        _report_error(e)
    if not cands:
        click.echo("未找到匹配结果。")
        return
    click.echo(f"TMDB 搜索结果（type={media_type}，共 {len(cands)} 条）")
    click.echo("类型 | tmdb_id | 标题(年份) | 原名 | 简介长度")
    for c in cands:
        year_str = f"({c.year})" if c.year else "(无年份)"
        click.echo(f"[{c.media_type}] | {c.tmdb_id} | {c.title} {year_str} | "
                   f"{c.original_title} | {c.overview_length}")


@cli.command(name="fetch-summary")
@click.argument("tmdb_id", type=int)
@click.option("--language", "-l", default="zh-CN")
@click.option("--season", type=int, default=None,
              help="只拉取并展示某一季的集列表（不再搜索整剧，用于确认命中后逐层下钻）")
@click.option("--episode-groups", "show_groups", is_flag=True,
              help="输出剧集组列表（默认不输出；用 episode-group <组ID> 查看组详情）")
def fetch_summary(tmdb_id, language, season, show_groups):
    """获取剧摘要（不含完整 overview）

    不带 --season：输出整剧摘要（季列表）。默认不输出剧集组，加 --episode-groups 输出。
    带 --season N：只拉取第 N 季的集列表（含每集名称与时长），不再搜索整剧——
    适合先确认整剧命中，再下钻看某季具体集信息。
    """
    logger.info("fetch-summary: id=%s season=%s groups=%s", tmdb_id, season, show_groups)

    try:
        # 下钻模式：只拉季集，不搜整剧
        if season is not None:
            eps = tmdb.get_season_episodes(tmdb_id, season, language=language)
            _print_season_episodes(tmdb_id, season, eps)
            return
        s = tmdb.get_show_summary(tmdb_id, language=language)
    except (RuntimeError, httpx.HTTPError) as e:
        _report_error(e)

    click.echo(f"tmdb_id={s.tmdb_id} | {s.title} ({s.year}) | original={s.original_title}")
    click.echo(f"季数={s.total_seasons} 总集数={s.total_episodes} "
               f"简介可用={'是' if s.overview_available else '否'} 简介长度={s.overview_length}")
    click.echo("季列表")
    click.echo("季号 | 名称 | 集数 | 首播日期 | 简介可用")
    for season_obj in s.seasons:
        click.echo(f"S{season_obj.season_number:02d} | {season_obj.name} | "
                   f"{season_obj.episode_count} | {season_obj.first_air_date or '无'} | "
                   f"{'是' if season_obj.overview_available else '否'}")
    if show_groups and s.episode_groups:
        click.echo("剧集组")
        click.echo("组ID | 名称 | 类型 | 集数")
        for g in s.episode_groups:
            click.echo(f"{g.id} | {g.name} | {g.type_name} | {g.episode_count}")


def _print_season_episodes(tmdb_id: int, season: int, eps) -> None:
    """打印某季集列表（表头列名 + 内容行）"""
    click.echo(f"TMDB id={tmdb_id} 第 {season} 季 集列表")
    click.echo("集号 | 名称 | 时长(分钟) | 简介长度")
    if not eps:
        click.echo("（无集数据）")
        return
    for e in eps:
        runtime = str(e.runtime) if e.runtime is not None else "无数据"
        click.echo(f"E{e.episode_number:02d} | {e.name} | {runtime} | {e.overview_length}")


@cli.command()
@click.argument("path", metavar="path")
@click.option("--json", "as_json", is_flag=True, help="以 JSON 输出（视频时长为秒数），默认输出树状文本")
@click.option("--out", type=click.Path(), default=None, help="结果输出文件路径（默认仅打印到 stdout）")
def analyze(path, as_json, out):
    """分析文件夹/文件路径结构（agent 执行的第一步）

    默认输出树状文本：首层显示绝对路径，深层只显示名字；视频时长用 HH:MM:SS，
    目录标注子树累计视频数。加 --json 输出 JSON（时长为秒数，含每个节点的完整路径）。
    目录深度≥5 或文件总数>5000 时，只返回概要并停止（避免对超大树逐个取时长）。
    """
    logger.info("analyze: path=%s json=%s", path, as_json)
    result = analyze_path(path)
    if as_json:
        output = result.model_dump(mode="json")
        text = json.dumps(output, ensure_ascii=False, indent=2)
    else:
        text = render_text(result)
    click.echo(text)
    if out:
        pathlib.Path(out).write_text(text, encoding="utf-8")


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
@click.option("--snapshot", type=click.Path(), default=None, help="事务日志保存路径（默认存到 ~/.melodyi-skills/melodyi-filebot/snapshots/ 下）")
def execute_plan_cmd(plan_path, execute, snapshot):
    """执行计划（默认 dry-run）

    真正执行（--execute）时一定会写事务日志，以便事后 undo：
    - 显式 --snapshot：写到指定路径
    - 未指定：默认写到 ~/.melodyi-skills/melodyi-filebot/snapshots/<plan文件名>.snapshot.json
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


# ---------- Bangumi ----------

@cli.command(name="bangumi-search")
@click.argument("keyword", metavar="keyword")
@click.option("--json", "as_json", is_flag=True, help="以 JSON 输出（含完整 summary）")
def bangumi_search(keyword, as_json):
    """搜索 Bangumi 动画条目（限定 type=2 动画，返回 ≤10 条）

    文本输出只含简介长度（不外泄完整 summary，agent 无需知道简介内容）；
    --json 输出完整 summary。
    """
    logger.info("bangumi-search: keyword=%r", keyword)
    try:
        cands = bangumi.search_anime(keyword)
    except (RuntimeError, httpx.HTTPError) as e:
        _report_error(e)
    if as_json:
        click.echo(json.dumps([c.model_dump(mode="json") for c in cands],
                              ensure_ascii=False, indent=2))
        return
    if not cands:
        click.echo("未找到匹配结果。")
        return
    click.echo(f"Bangumi 搜索结果（共 {len(cands)} 条）")
    click.echo("bangumi_id | 中文名 | 原名 | 放送日期 | 集数 | 平台 | 简介长度")
    for c in cands:
        click.echo(f"{c.subject_id} | {c.name_cn} | {c.name} | {c.date or '无'} | "
                   f"{c.eps} | {c.platform or '无'} | {c.summary_length}")


@cli.command(name="bangumi-subject")
@click.argument("subject_id", type=int)
@click.option("--json", "as_json", is_flag=True, help="以 JSON 输出（含完整 summary）")
def bangumi_subject(subject_id, as_json):
    """获取 Bangumi 条目详情

    文本输出只含简介长度；--json 输出完整 summary。
    """
    logger.info("bangumi-subject: id=%s", subject_id)
    try:
        s = bangumi.get_subject(subject_id)
    except (RuntimeError, httpx.HTTPError) as e:
        _report_error(e)
    if as_json:
        click.echo(s.model_dump_json(indent=2, ensure_ascii=False))
        return
    click.echo(f"bangumi_id={s.subject_id} | {s.name_cn} / {s.name}")
    click.echo(f"放送日期={s.date or '无'} | 集数={s.eps} | 平台={s.platform or '无'} | "
               f"简介可用={'是' if s.summary_available else '否'} | 简介长度={s.summary_length}")


@cli.command(name="bangumi-episodes")
@click.argument("subject_id", type=int)
@click.option("--type", "ep_type", type=int, default=0,
              help="集类型（0=本篇 1=特别篇 2=OP 3=ED 4=预告 5=MAD 6=其他 7=非正片，默认 0）")
@click.option("--json", "as_json", is_flag=True, help="以 JSON 输出（含完整 desc）")
def bangumi_episodes(subject_id, ep_type, as_json):
    """获取 Bangumi 条目集列表（自动翻页）

    文本输出只含简介长度；--json 输出完整 desc。
    """
    logger.info("bangumi-episodes: id=%s type=%s", subject_id, ep_type)
    try:
        eps = bangumi.get_subject_episodes(subject_id, ep_type=ep_type)
    except (RuntimeError, httpx.HTTPError) as e:
        _report_error(e)
    if as_json:
        click.echo(json.dumps([e.model_dump(mode="json") for e in eps],
                              ensure_ascii=False, indent=2))
        return
    click.echo(f"Bangumi id={subject_id} type={ep_type} 集列表（共 {len(eps)} 集）")
    click.echo("集号 | 中文名 | 原名 | 放送日期 | 时长 | 简介长度")
    if not eps:
        click.echo("（无集数据）")
        return
    for e in eps:
        ep_label = f"E{e.ep:02d}" if e.ep is not None else f"sort{e.sort:g}"
        runtime = e.duration or "无数据"
        click.echo(f"{ep_label} | {e.name_cn} | {e.name} | {e.airdate or '无'} | "
                   f"{runtime} | {e.desc_length}")


@cli.command(name="episode-group")
@click.argument("group_id", metavar="group_id")
@click.option("--language", "-l", default="zh-CN")
@click.option("--json", "as_json", is_flag=True, help="以 JSON 输出")
def episode_group(group_id, language, as_json):
    """获取 TMDB 剧集组详情（子组 + 集列表）

    用于非标场景1：重置版等归在剧集组而非独立季时，用此命令查看组的子组结构与每集信息。
    组 ID 可由 `fetch-summary <tmdb_id> --episode-groups` 获取。
    """
    logger.info("episode-group: group_id=%s", group_id)
    try:
        d = tmdb.get_episode_group(group_id, language=language)
    except (RuntimeError, httpx.HTTPError) as e:
        _report_error(e)
    if as_json:
        click.echo(d.model_dump_json(indent=2, ensure_ascii=False))
        return
    click.echo(f"组ID={d.id} | {d.name} | 类型={d.type_name} | 集数={d.episode_count} | 子组数={d.group_count}")
    for sg in d.sub_groups:
        click.echo(f"子组: {sg.name or '（未命名）'}")
        click.echo("集号 | 名称 | 放送日期 | 时长 | 简介长度")
        if not sg.episodes:
            click.echo("（无集数据）")
            continue
        for e in sg.episodes:
            ep_label = f"S{e.season_number:02d}E{e.episode_number:02d}" if e.season_number is not None else f"E{e.episode_number:02d}"
            runtime = str(e.runtime) if e.runtime is not None else "无数据"
            click.echo(f"{ep_label} | {e.name} | {e.air_date or '无'} | {runtime} | {e.overview_length}")


if __name__ == "__main__":
    cli()
