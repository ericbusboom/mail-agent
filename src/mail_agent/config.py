import os
from pathlib import Path
from typing import Any, Dict, List, Tuple

from dotenv import dotenv_values


class Config:


    def __init__(self, config_dict: Dict[str, Any]):
        self._config_dict = config_dict

    @classmethod
    def load(cls, config_dir: str | Path, deploy: str = "devel") -> "Config":
        """
        Load configuration from .env files in the specified directory and return a new Config object.
        """
        
        config_dir = Path(config_dir) if isinstance(config_dir, str) else config_dir

        if config_dir is None or not config_dir.is_dir():
            raise ValueError(f"Invalid config_dir: {config_dir}. It must be a valid directory path.")

        secrets_dir = Path(config_dir) / "secrets"

        config_files = [
            config_dir  / f"config.env",
            config_dir  / f"{deploy}.env",
            secrets_dir / "secrets.env",
            secrets_dir / f"{deploy}.env",
        ]

        config_dict = {}
        loaded_files = []

        for config_file in config_files:

            if config_file.exists():
                config_dict.update(dotenv_values(config_file))
                loaded_files.append(config_file)

        config_dict['__loaded_files__'] = loaded_files
        config_dict['__config_dir__'] = str(config_dir)
        config_dict['__secrets_dir__'] = str(secrets_dir)
        config_dict['__deploy__'] = deploy

        # For the environment, only load if the  value in the config is __ENV__
        for key, value in config_dict.items():
            if value == "__ENV__":
                env_value = os.getenv(key)
                if env_value is not None:
                    config_dict[key] = env_value



        return cls(config_dict)

    def get_file_path(self, file_name) -> Path:
        """
        Return the absolute path of a file in either the config or secrets directory.
        """
        config_dir = Path(self._config_dict['__config_dir__'])
        secrets_dir = Path(self._config_dict['__secrets_dir__'])

        if (config_dir / file_name).exists():
            return config_dir / file_name
        elif (secrets_dir / file_name).exists():
            return secrets_dir / file_name
        else:
            raise FileNotFoundError(f"File {file_name} not found in config or secrets directory.")

    def __setattr__(self, name: str, value: Any) -> None:
        if name == "_config_dict":
            super().__setattr__(name, value)
        else:
            self._config_dict[name] = value

    def __getattr__(self, name: str) -> Any:
        try:
            return self._config_dict[name]
        except KeyError:
            raise AttributeError(f"'Config' object has no attribute '{name}'")

    def __getitem__(self, key: str) -> Any:
        return self._config_dict[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self._config_dict[key] = value

    def __delitem__(self, key: str) -> None:
        del self._config_dict[key]

    def __contains__(self, key: str) -> bool:
        return key in self._config_dict

    def get(self, key: str, default: Any = None) -> Any:
        return self._config_dict.get(key, default)

    def keys(self) -> List[str]:
        return list(self._config_dict.keys())

    def values(self) -> List[Any]:
        return list(self._config_dict.values())

    def items(self) -> List[Tuple[str, Any]]:
        return list(self._config_dict.items())

    def to_dict(self) -> Dict[str, Any]:
        return self._config_dict.copy()

