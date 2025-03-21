from aiohttp import web
from webargs.aiohttpparser import AIOHTTPParser

# TODO: make it web.AppKey in 1.x release
# Leave as a string for backward compatibility with 0.x
SWAGGER_DICT = "swagger_dict"

APISPEC_VALIDATED_DATA_NAME = web.AppKey("_apispec_validated_data_name", str)
APISPEC_PARSER = web.AppKey("_apispec_parser", AIOHTTPParser)

# TODO: make __apispec__ and __schemas__ typed objects in 1.x release
API_SPEC_ATTR = "__apispec__"
SCHEMAS_ATTR = "__schemas__"
