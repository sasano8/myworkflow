"""Business outlines only; these functions do not implement the web application."""

from myworkflow import step
from myworkflow.runtime.context import Context
from .definitions import (
    ProjectQuery,
    ProjectList,
    ProjectRequest,
    Project,
    Settings,
    Template,
    ChatRequest,
    ChangeSet,
    BuildRequest,
    BuildResult,
    DisplayedVersion,
    DeletionResult,
)


@step(
    id="web.s.list_projects",
    name="一覧の取得",
    summary="設定DBから利用者のプロジェクト一覧を取得する。業務契約の正本はコードとし、DBは運用情報だけを管理する。",
    reads=(ProjectQuery,),
    writes=(ProjectList,),
    uses=((ProjectQuery, "参照"), (ProjectList, "保持")),
    extensions={"requirements": ("WEB-001", "WEB-017")},
)
def list_projects(ctx: Context) -> None:
    raise NotImplementedError("Requirements outline only")


@step(
    id="web.s.create_project",
    name="プロジェクトの作成",
    summary="プロジェクトを作成し、専用の詳細画面へ進めるようにする。",
    reads=(ProjectRequest,),
    writes=(Project,),
    uses=((ProjectRequest, "参照"), (Project, "保持")),
    extensions={"requirements": ("WEB-002", "WEB-003")},
)
def create_project(ctx: Context) -> None:
    raise NotImplementedError("Requirements outline only")


@step(
    id="web.s.save_settings",
    name="GitHub接続と開発ガイドの設定",
    summary="GitHub保存先とプロジェクトの開発ガイドを設定する。push先と作業ブランチの戦略を持つが、選択肢・既定値・PRやマージの方針は未決とする。",
    reads=(Project, Settings),
    writes=(Settings,),
    uses=((Project, "参照"), (Settings, "参照")),
    extensions={"requirements": ("WEB-004", "WEB-005", "WEB-014", "WEB-015")},
)
def save_settings(ctx: Context) -> None:
    raise NotImplementedError("Requirements outline only")


@step(
    id="web.s.manage_template",
    name="開発ガイドテンプレートの管理",
    summary="プロジェクト設定とは独立した画面で共通の開発ガイドテンプレートを管理する。編集・適用・更新の伝播方法は未決とする。",
    reads=(Template,),
    writes=(Template,),
    uses=((Template, "参照"),),
    extensions={"requirements": ("WEB-016",)},
)
def manage_template(ctx: Context) -> None:
    raise NotImplementedError("Requirements outline only")


@step(
    id="web.s.prepare_environment",
    name="開発環境の準備",
    summary="対象プロジェクトの開発環境を自動準備する。Codespacesなどの具体的な基盤は未決とする。",
    reads=(ChatRequest,),
    writes=(),
    uses=((ChatRequest, "参照"),),
    extensions={"requirements": ("WEB-010",)},
)
def prepare_environment(ctx: Context) -> None:
    raise NotImplementedError("Requirements outline only")


@step(
    id="web.s.apply_requirements",
    name="対話した要件をコードへ反映",
    summary="会話を元にコードの業務契約を変更し、会話・基準版とコード差分を結び付ける。DBに業務契約の別正本を作らない。対象ソース版を特定した自動ビルド依頼を作る。",
    reads=(ChatRequest,),
    writes=(ChangeSet, BuildRequest),
    uses=((ChatRequest, "参照"), (ChangeSet, "保持"), (BuildRequest, "保持")),
    extensions={"requirements": ("WEB-008", "WEB-009", "WEB-017", "WEB-020")},
)
def apply_requirements(ctx: Context) -> None:
    raise NotImplementedError("Requirements outline only")


@step(
    id="web.s.build_preview",
    name="文書生成・検証とプレビュー作成",
    summary="固定したソース版から業務要件を生成・検証する。会話・コード差分・検証結果・表示版を追跡できるようにする。成功時にプレビューを更新し、失敗時は最後の成功版を維持する。初回失敗は未生成と表示する。ビルド成功を保存・マージの確定とはせず、開発ガイドの戦略を別途適用する。",
    reads=(BuildRequest,),
    writes=(BuildResult,),
    uses=((BuildRequest, "参照"), (BuildResult, "保持")),
    extensions={
        "requirements": (
            "WEB-009",
            "WEB-011",
            "WEB-012",
            "WEB-018",
            "WEB-019",
            "WEB-020",
        )
    },
)
def build_preview(ctx: Context) -> None:
    raise NotImplementedError("Requirements outline only")


@step(
    id="web.s.show_documents",
    name="ドキュメントの閲覧",
    summary="プロジェクトの文書トップページを表示する。表示中のコミットと最新コードとの差分、対応する会話・変更・検証結果を示す。MkDocsの表示・隔離方式は未決とする。",
    reads=(Project,),
    writes=(DisplayedVersion,),
    uses=((Project, "参照"), (DisplayedVersion, "保持")),
    extensions={"requirements": ("WEB-006", "WEB-007", "WEB-018", "WEB-020")},
)
def show_documents(ctx: Context) -> None:
    raise NotImplementedError("Requirements outline only")


@step(
    id="web.s.delete_project",
    name="プロジェクトの削除",
    summary="プロジェクトを削除する。進行中ジョブ・環境・保存データの整理と保持期間、GitHubリポジトリの扱いは未決とする。",
    reads=(Project,),
    writes=(DeletionResult,),
    uses=((Project, "参照"), (DeletionResult, "保持")),
    extensions={"requirements": ("WEB-013",)},
)
def delete_project(ctx: Context) -> None:
    raise NotImplementedError("Requirements outline only")
