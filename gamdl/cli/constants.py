EXCLUDED_CONFIG_FILE_PARAMS = {
    "urls",
    "config_path",
    "read_urls_as_txt",
    "no_config_file",
    "version",
    "help",
}
# Upstream gamdl misspells this key; carry it over so an upstream config.ini
# keeps its codec priority instead of being reset to the default.
LEGACY_CONFIG_FILE_PARAMS = {
    "song_codec_piority": "song_codec_priority",
}
X_NOT_IN_PATH = '{} was not found in PATH at "{}"'
