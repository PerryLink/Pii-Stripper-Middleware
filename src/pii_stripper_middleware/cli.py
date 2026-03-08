"""
命令行界面（CLI）模块。

提供三个子命令：
  strip   - 仅脱敏文本，不发送给 AI
  chat    - 脱敏后发送给 OpenAI，收到回复后还原 PII
  demo    - 无需 API Key 的本地演示
"""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from pii_stripper_middleware.core import PIIStripper
from pii_stripper_middleware.utils import chat_completion, get_openai_client, load_env

# ---------------------------------------------------------------------------
# Typer 应用
# ---------------------------------------------------------------------------

app = typer.Typer(
    name="pii-stripper",
    help="[bold cyan]🔒 PII Stripper Middleware[/bold cyan] — 自动脱敏，安全对话",
    add_completion=False,
    rich_markup_mode="rich",
    no_args_is_help=True,
)

console = Console()
err_console = Console(stderr=True, style="bold red")

# ---------------------------------------------------------------------------
# 内部辅助函数
# ---------------------------------------------------------------------------


def _show_strip_panel(original: str, anonymized: str, mapping: dict[str, str]) -> None:
    """以 Rich 面板格式展示脱敏前后对比及映射表。"""
    console.print()
    console.print(Panel(original, title="[red]原始文本[/red]", border_style="red"))
    console.print(Panel(
        f"[bold green]{anonymized}[/bold green]",
        title="[green]脱敏后文本[/green]",
        border_style="green",
    ))
    if mapping:
        table = Table(title="替换映射表", header_style="bold cyan", show_lines=True)
        table.add_column("占位符", style="cyan", no_wrap=True)
        table.add_column("原始值", style="yellow")
        for placeholder, original_val in mapping.items():
            table.add_row(placeholder, original_val)
        console.print(table)


def _do_single_chat(
    client,
    stripper: PIIStripper,
    text: str,
    model: str,
    verbose: bool,
) -> None:
    """执行一次脱敏→请求→还原流程并打印结果。"""
    with console.status("[bold green]正在检测 PII...[/bold green]"):
        anonymized = stripper.strip(text)

    if verbose:
        _show_strip_panel(text, anonymized, stripper.mapping)
        console.print()

    with console.status(f"[bold blue]正在请求 {model}...[/bold blue]"):
        raw_response = chat_completion(client, anonymized, model=model)

    restored = stripper.restore(raw_response)

    if verbose:
        console.print(Panel(
            f"[dim]{raw_response}[/dim]",
            title="[yellow]AI 原始回复（含占位符）[/yellow]",
            border_style="yellow",
        ))

    console.print(Panel(
        restored,
        title="[bold green]AI 回复[/bold green]",
        border_style="green",
    ))


def _run_interactive_chat(
    client,
    stripper: PIIStripper,
    model: str,
    verbose: bool,
) -> None:
    """启动交互式 REPL 对话模式。"""
    console.print(Panel(
        "[bold]欢迎使用 PII 脱敏对话助手！[/bold]\n\n"
        "您的消息将自动脱敏后发送给 AI，回复中的占位符会自动还原。\n"
        "命令：[bold red]quit / exit[/bold red] 退出，"
        "[bold yellow]clear[/bold yellow] 清空历史，"
        "[bold cyan]mapping[/bold cyan] 查看上一条映射",
        title="[bold cyan]🔒 PII Stripper Chat[/bold cyan]",
        border_style="cyan",
    ))

    history: list[dict] = []

    while True:
        try:
            user_input = Prompt.ask("\n[bold cyan]你[/bold cyan]")
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]再见！[/dim]")
            break

        cmd = user_input.strip().lower()

        if cmd in ("quit", "exit", "q"):
            console.print("[dim]再见！[/dim]")
            break

        if cmd == "clear":
            history.clear()
            console.print("[dim]对话历史已清空[/dim]")
            continue

        if cmd == "mapping":
            if stripper.mapping:
                _show_strip_panel("（上一条消息）", "（见映射表）", stripper.mapping)
            else:
                console.print("[dim]暂无映射记录[/dim]")
            continue

        if not user_input.strip():
            continue

        # 脱敏
        anonymized = stripper.strip(user_input)

        if verbose and stripper.mapping:
            table = Table(title="本轮脱敏", header_style="bold dim", show_lines=True)
            table.add_column("占位符", style="cyan")
            table.add_column("原始值", style="yellow")
            for ph, orig in stripper.mapping.items():
                table.add_row(ph, orig)
            console.print(table)

        # 请求 AI
        try:
            with console.status(f"[bold blue]正在请求 {model}...[/bold blue]"):
                raw_response = chat_completion(
                    client, anonymized, model=model, history=history
                )
        except Exception as exc:
            err_console.print(f"请求失败：{exc}")
            continue

        # 更新历史（存储脱敏文本，避免历史中出现真实 PII）
        history.append({"role": "user", "content": anonymized})
        history.append({"role": "assistant", "content": raw_response})

        restored = stripper.restore(raw_response)

        if verbose:
            console.print(f"[dim]AI 原始回复（含占位符）：{raw_response}[/dim]")

        console.print(f"\n[bold green]AI[/bold green]: {restored}\n")


# ---------------------------------------------------------------------------
# 子命令：strip
# ---------------------------------------------------------------------------


@app.command()
def strip(
    text: Optional[str] = typer.Argument(None, help="要脱敏的文本"),
    file: Optional[Path] = typer.Option(None, "--file", "-f", help="输入文件路径"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="输出文件路径"),
    show_mapping: bool = typer.Option(
        True, "--show-mapping/--no-show-mapping", help="是否显示替换映射表"
    ),
    no_nlp: bool = typer.Option(False, "--no-nlp", help="禁用 NLP，仅使用正则表达式"),
    env_file: Optional[Path] = typer.Option(None, "--env-file", help=".env 文件路径"),
) -> None:
    """
    [bold]🔍 脱敏文本中的 PII 信息。[/bold]

    示例：

      pii-stripper strip "联系张三，手机 13812345678"

      pii-stripper strip --file input.txt --output output.txt
    """
    load_env(env_file)

    if file:
        if not file.exists():
            err_console.print(f"文件不存在：{file}")
            raise typer.Exit(1)
        input_text = file.read_text(encoding="utf-8")
    elif text:
        input_text = text
    else:
        err_console.print("错误：请提供文本参数或 --file 文件路径。")
        raise typer.Exit(1)

    stripper = PIIStripper(use_nlp=not no_nlp)

    with console.status("[bold green]正在检测 PII...[/bold green]"):
        anonymized = stripper.strip(input_text)

    if show_mapping:
        _show_strip_panel(input_text, anonymized, stripper.mapping)
    else:
        console.print(anonymized)

    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(anonymized, encoding="utf-8")
        console.print(f"\n[dim]结果已保存到：{output}[/dim]")


# ---------------------------------------------------------------------------
# 子命令：chat
# ---------------------------------------------------------------------------


@app.command()
def chat(
    text: Optional[str] = typer.Argument(None, help="发送给 AI 的文本"),
    model: str = typer.Option("gpt-4o-mini", "--model", "-m", help="OpenAI 模型名称"),
    interactive: bool = typer.Option(
        False, "--interactive", "-i", help="启动交互式对话模式"
    ),
    api_key: Optional[str] = typer.Option(None, "--api-key", help="OpenAI API Key"),
    base_url: Optional[str] = typer.Option(
        None, "--base-url", help="API Base URL（用于代理或兼容端点）"
    ),
    no_nlp: bool = typer.Option(False, "--no-nlp", help="禁用 NLP，仅使用正则表达式"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="显示脱敏过程详情"),
    env_file: Optional[Path] = typer.Option(None, "--env-file", help=".env 文件路径"),
) -> None:
    """
    [bold]💬 脱敏后安全地与 OpenAI 对话。[/bold]

    示例：

      pii-stripper chat "帮我给张三发邮件，他的号码是 13812345678"

      pii-stripper chat --interactive --verbose

      pii-stripper chat "..." --base-url https://your-proxy.com/v1
    """
    load_env(env_file)

    try:
        client = get_openai_client(api_key=api_key, base_url=base_url)
    except (ValueError, ImportError) as exc:
        err_console.print(str(exc))
        raise typer.Exit(1)

    stripper = PIIStripper(use_nlp=not no_nlp)

    if interactive:
        _run_interactive_chat(client, stripper, model, verbose)
    elif text:
        try:
            _do_single_chat(client, stripper, text, model, verbose)
        except Exception as exc:
            err_console.print(f"请求失败：{exc}")
            raise typer.Exit(1)
    else:
        err_console.print(
            "错误：请提供文本参数，或使用 --interactive 启动交互模式。"
        )
        raise typer.Exit(1)


# ---------------------------------------------------------------------------
# 子命令：demo
# ---------------------------------------------------------------------------


@app.command()
def demo(
    no_nlp: bool = typer.Option(True, "--no-nlp/--nlp", help="是否禁用 NLP（默认禁用以提高演示稳定性）"),
) -> None:
    """
    [bold]🎭 无需 API Key，本地演示 PII 脱敏效果。[/bold]
    """
    console.print(Panel(
        "[bold cyan]PII Stripper Middleware — 本地演示[/bold cyan]\n\n"
        "展示自动检测并替换个人隐私信息的核心能力\n"
        "[dim]（本演示不会调用任何 API，数据不离开本机）[/dim]",
        title="🔒 演示模式",
        border_style="cyan",
    ))

    demo_cases = [
        (
            "CRM 工单",
            "客户张三反映账单有误，请联系他：手机 13812345678，"
            "邮箱 zhangsan@example.com，身份证 110101199001011234。",
        ),
        (
            "客服记录",
            "李四（18987654321）昨天来访，邮件地址 lisi@company.com，"
            "要求退款订单 #20240301。",
        ),
        (
            "审计日志",
            "操作员 wangwu@corp.cn 于 2024-03-01 从 192.168.1.100 登录，"
            "修改了账户 ID 320112198506154321 的权限。",
        ),
    ]

    stripper = PIIStripper(use_nlp=not no_nlp)

    for i, (label, text) in enumerate(demo_cases, 1):
        console.rule(f"[bold yellow]示例 {i}：{label}[/bold yellow]")
        anonymized = stripper.strip(text)
        _show_strip_panel(text, anonymized, stripper.mapping)
        console.print()

    console.print(
        Panel(
            "[bold green]✅ 演示完成！[/bold green]\n\n"
            "以上所有敏感信息均已被替换为占位符。\n"
            "在实际使用中，AI 处理完毕后，占位符会自动还原为原始值。\n\n"
            "运行 [bold cyan]pii-stripper chat --interactive[/bold cyan] 开始真实对话。",
            border_style="green",
        )
    )
