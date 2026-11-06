"""Canonical annotated requirements; Markdown is generated from these declarations."""

from dataclasses import dataclass
from typing import Literal
from myworkflow import annotate, declaration


@dataclass(frozen=True)
class Requirement:
    id: str
    name: str
    summary: str
    scope: Literal["core", "support"] = "core"


def requirement(
    *, id: str, name: str, summary: str, scope: Literal["core", "support"] = "core"
):
    return annotate(Requirement(id, name, summary, scope))


@requirement(
    id="WEB-001",
    name="プロジェクト一覧の表示",
    summary="プロジェクト一覧を表示する",
    scope="support",
)
class ProjectListing:
    pass


@requirement(
    id="WEB-002",
    name="プロジェクト作成",
    summary="プロジェクトを作成できる",
    scope="support",
)
class ProjectCreation:
    pass


@requirement(
    id="WEB-003",
    name="プロジェクト詳細の表示",
    summary="選択したプロジェクトの専用ページを表示する",
    scope="core",
)
class ProjectDetails:
    pass


@requirement(
    id="WEB-004",
    name="設定画面を開く",
    summary="プロジェクトの設定画面を持つ",
    scope="core",
)
class ProjectSettings:
    pass


@requirement(
    id="WEB-005",
    name="GitHub保存先の設定",
    summary="保存先にGitHubを指定できる",
    scope="core",
)
class GitHubDestination:
    pass


@requirement(
    id="WEB-006",
    name="文書トップページの表示",
    summary="ドキュメントのトップページを表示する",
    scope="core",
)
class DocumentTop:
    pass


@requirement(
    id="WEB-007",
    name="MkDocs文書の閲覧",
    summary="プロジェクトのMkDocsサイトをそのまま閲覧する体験を目指す。表示方式は未決",
    scope="core",
)
class MkDocsViewing:
    pass


@requirement(
    id="WEB-008",
    name="対話による要件入力",
    summary="利用者が対話で要件を伝えられる",
    scope="core",
)
class RequirementChat:
    pass


@requirement(
    id="WEB-009",
    name="要件のコード・文書反映",
    summary="対話内容をコードへ反映し、対応するドキュメントを生成する",
    scope="core",
)
class RequirementReflection:
    pass


@requirement(
    id="WEB-010",
    name="開発環境の自動準備",
    summary="Codespacesなどで開発環境を自動準備する。提供基盤は未決",
    scope="core",
)
class DevelopmentEnvironment:
    pass


@requirement(
    id="WEB-011", name="手動ビルド", summary="手動ビルドボタンを持つ", scope="core"
)
class ManualBuild:
    pass


@requirement(
    id="WEB-012",
    name="要件反映後の自動ビルド",
    summary="チャットによる要件反映後に自動ビルドできる",
    scope="core",
)
class AutomaticBuild:
    pass


@requirement(
    id="WEB-013",
    name="プロジェクト削除",
    summary="プロジェクトを削除できる",
    scope="support",
)
class ProjectDeletion:
    pass


@requirement(
    id="WEB-014",
    name="開発ガイド設定画面",
    summary="プロジェクトごとに開発ガイドを設定する画面を持つ",
    scope="core",
)
class DevelopmentGuide:
    pass


@requirement(
    id="WEB-015",
    name="push先・ブランチ戦略の設定",
    summary="push先と作業ブランチの切り方の戦略を設定する。選択肢・既定値は未決",
    scope="core",
)
class BranchStrategy:
    pass


@requirement(
    id="WEB-016",
    name="開発ガイドテンプレートの管理",
    summary="プロジェクトの設定画面とは別に、開発ガイドテンプレートを管理する画面を持つ",
    scope="support",
)
class GuideTemplateManagement:
    pass


@requirement(
    id="WEB-017",
    name="コードを業務契約の正本にする",
    summary="業務契約はコードを正本とし、DBでは設定・会話・実行履歴を管理する。業務契約を二重管理しない",
    scope="core",
)
class CodeAsSource:
    pass


@requirement(
    id="WEB-018",
    name="最後の成功版と版の差分を表示する",
    summary="ビルド失敗時は最後の成功版を維持し、表示中のコミットと最新コードの版・差分を明示する。初回失敗なら未生成と表示する",
    scope="core",
)
class LastSuccessfulVersion:
    pass


@requirement(
    id="WEB-019",
    name="自動プレビューと確定を分離する",
    summary="要件反映後に自動プレビューを作成する。ビルド成功だけを理由に保存・マージを確定しない",
    scope="core",
)
class PreviewBeforeFinalization:
    pass


@requirement(
    id="WEB-020",
    name="会話から表示版まで追跡する",
    summary="会話からコード差分・検証結果・表示版を相互にたどれる",
    scope="core",
)
class ChangeTraceability:
    pass


REQUIREMENTS = (
    ProjectListing,
    ProjectCreation,
    ProjectDetails,
    ProjectSettings,
    GitHubDestination,
    DocumentTop,
    MkDocsViewing,
    RequirementChat,
    RequirementReflection,
    DevelopmentEnvironment,
    ManualBuild,
    AutomaticBuild,
    ProjectDeletion,
    DevelopmentGuide,
    BranchStrategy,
    GuideTemplateManagement,
    CodeAsSource,
    LastSuccessfulVersion,
    PreviewBeforeFinalization,
    ChangeTraceability,
)


def requirement_ids(*targets):
    return tuple(declaration(target).id for target in targets)
