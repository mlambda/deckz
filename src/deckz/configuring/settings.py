from functools import reduce
from pathlib import Path
from typing import Annotated, Any, Self

from appdirs import user_config_dir as appdirs_user_config_dir
from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    PlainValidator,
    ValidationInfo,
)

from .. import app_name
from ..exceptions import DeckzError
from ..utils import get_git_dir, intermediate_dirs, load_all_yamls


def value_from_settings(value: str, info: ValidationInfo) -> Any:
    if not isinstance(info.context, GlobalSettings):
        msg = "context should be an instance of Settings"
        raise ValueError(msg)
    settings = info.context
    path = value.split(".")
    current = settings
    for item in path:
        try:
            current = getattr(current, item)
        except AttributeError as e:
            msg = f"impossible to map the setting path {value} to a setting: {e}"
            raise ValueError(msg) from e
    return current


ValueFromSettingsValidator = PlainValidator(value_from_settings)
PathFromSettings = Annotated[Path, ValueFromSettingsValidator]
StrFromSettings = Annotated[str, ValueFromSettingsValidator]


def _convert(input_value: str | Path, info: ValidationInfo) -> Path:
    if isinstance(input_value, str):
        return Path(input_value.format(**info.data))
    return input_value


_Path = Annotated[Path, BeforeValidator(_convert), AfterValidator(Path.resolve)]


# ruff: noqa: RUF027
# mypy: ignore-errors
class GlobalPaths(BaseModel):
    model_config = ConfigDict(validate_default=True)
    current_dir: _Path
    git_dir: _Path = Field(
        default_factory=lambda data: get_git_dir(data["current_dir"])
    )
    settings: _Path = "{git_dir}/settings.yml"
    shared_dir: _Path = "{git_dir}/shared"
    figures_dir: _Path = "{git_dir}/figures"
    shared_img_dir: _Path = "{shared_dir}/img"
    shared_code_dir: _Path = "{shared_dir}/code"
    shared_latex_dir: _Path = "{shared_dir}/latex"
    shared_tikz_pdf_dir: _Path = "{shared_dir}/tikz"
    shared_plt_pdf_dir: _Path = "{shared_dir}/plt"
    shared_plotly_pdf_dir: _Path = "{shared_dir}/pltly"
    templates_dir: _Path = "{git_dir}/templates"
    plt_dir: _Path = "{figures_dir}/plots"
    plotly_dir: _Path = "{figures_dir}/pltly"
    tikz_dir: _Path = "{figures_dir}/tikz"
    jinja2_dir: _Path = "{templates_dir}/jinja2"
    jinja2_main_template: _Path = "{jinja2_dir}/main.tex"
    user_config_dir: _Path = Field(
        default_factory=lambda: Path(appdirs_user_config_dir(app_name))
    )
    global_variables: _Path = "{git_dir}/global-variables.yml"
    github_issues: _Path = "{user_config_dir}/github-issues.yml"
    mails: _Path = "{user_config_dir}/mails.yml"
    gdrive_secrets: _Path = "{user_config_dir}/gdrive-secrets.json"
    gdrive_credentials: _Path = "{user_config_dir}/gdrive-credentials.pickle"
    user_variables: _Path = "{user_config_dir}/user-variables.yml"

    def model_post_init(self, __context: Any) -> None:
        for field, value in self.__dict__.items():
            setattr(self, field, value.resolve())
        self.user_config_dir.mkdir(parents=True, exist_ok=True)


def _company_variables_factory(data: dict[str, Any]) -> Path:
    if not data["current_dir"].relative_to(data["git_dir"]).match("*/*"):
        msg = (
            f"not deep enough from root {data['git_dir']}. "
            "Please follow the directory hierarchy root > company > deck and "
            "invoke this tool from the deck directory"
        )
        raise DeckzError(msg)
    return (
        data["git_dir"]
        / data["current_dir"].relative_to(data["git_dir"]).parts[0]
        / "company-variables.yml"
    )


class DeckPaths(GlobalPaths):
    build_dir: _Path = "{current_dir}/.build"
    pdf_dir: _Path = "{current_dir}/pdf"
    local_latex_dir: _Path = "{current_dir}/latex"
    company_variables: _Path = Field(default_factory=_company_variables_factory)
    deck_variables: _Path = "{current_dir}/deck-variables.yml"
    session_variables: _Path = "{current_dir}/session-variables.yml"
    deck_definition: _Path = "{current_dir}/deck.yml"


class Components(BaseModel):
    model_config = ConfigDict(extra="allow")


class GlobalSettings(BaseModel):
    paths: GlobalPaths = Field(default_factory=GlobalPaths)
    components: Components = Field(default_factory=Components)

    @classmethod
    def from_yaml(cls, path: Path) -> Self:
        resolved_path = path.resolve()
        git_dir = get_git_dir(resolved_path).resolve()
        if not resolved_path.is_relative_to(git_dir):
            msg = f"{path} is not relative to {git_dir}, cannot load settings"
            raise DeckzError(msg)
        content: dict[str, Any] = reduce(
            lambda a, b: {**a, **b},
            load_all_yamls(
                p / "deckz.yml" for p in intermediate_dirs(git_dir, resolved_path)
            ),
            {},
        )
        if "paths" not in content:
            content["paths"] = {}
        if "current_dir" not in content["paths"]:
            content["paths"]["current_dir"] = path
        return cls.model_validate(content)


class DeckSettings(GlobalSettings):
    paths: DeckPaths = Field(default_factory=DeckPaths)
