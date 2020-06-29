import base64
import json
import traceback
from contextlib import contextmanager
from pprint import pprint

import pendulum
from loguru import logger
from tinyrpc import InvalidReplyError
from tinyrpc.client import RPCClient, RPCProxy
from tinyrpc.protocols.jsonrpc import (
    JSONRPCSuccessResponse,
    JSONRPCErrorResponse,
    JSONRPCProtocol,
)
from tinyrpc.transports.http import HttpPostClientTransport


class LimeAPI:
    """
    LimeSurvey API Client for Remote API 2.
        Aims to simplify and automate the necessary task of moving data out of
        LimeSurvey without having to pull it directly from the site. Most of the
        communication between the remote LimeSurvey instance and the API follows
        the JSON-RPC 2 protocol.
        request and response validation to help keep communication more consistent.
    """

    # The following defaults are defined in a configuration file. See `settings.py` for
    # more details.
    _default_headers = {"content-type": "application/json", "connection": "Keep-Alive"}

    # There are still a few pain points in dealing with the JSON-RPC protocol
    _rpc_protocol_patched = False

    def __init__(self, url, username, password, headers=None):
        """
        LimeSurvey API Client for Remote API 2.
        Aims to simplify and automate the necessary task of moving data out of
        LimeSurvey in one way or another.
        :param url:     Fully-qualified LimeSurvey server URL containing protocol,
                        hostname, port, and the endpoint for the Remote Control 2 API.
        :param username: LimeSurvey account username
        :param password: LimeSurvey account password
        :param headers: Headers to include when making requests. At a minimum, each
                        request should be fitted with an application/JSON content-type
                        declaration
        """
        logger.info("Instantiating LimeAPI client")
        self.url = url
        self.username = username
        self.password = password
        self.headers = self._default_headers if headers is None else headers
        self.session_key = None
        self.rpc_client = None
        self.rpc_proxy = None
        self._authenticated = False

        self._validate_settings()

    @property
    def remote_api_url(self):
        return "/".join([self.url.rstrip("/"), "/index.php/admin/remotecontrol"])

    def authenticate(self):
        """
        Performs authentication actions
        Patches `tinyrpc` to remove minor incompatibilities due to JSON-RPC
        protocol version differences. This is performed once.
        Initializes the RPCClient and RPCProxy instances that
        are used to make the requests to Lime.
        :return: None
        """
        logger.info("Authenticating LimeAPI client")
        if not LimeAPI._rpc_protocol_patched:
            LimeAPI.patch_json_rpc_protocol()
            LimeAPI._rpc_protocol_patched = True
        self.rpc_client = RPCClient(
            JSONRPCProtocol(),
            HttpPostClientTransport(endpoint=self.remote_api_url, headers=self.headers),
        )

        self.rpc_proxy = self.rpc_client.get_proxy()
        self.session_key = self.rpc_proxy.get_session_key(
            username=self.username, password=self.password
        )
        if not self._validate_session_key():
            raise Exception(
                f"Failed to validate session key: url={self.url} "
                f"session_key={self.session_key}"
            )
        self._authenticated = True
        logger.info(f"Acquired session key: {self.session_key}")

    def list_surveys(self, username=None):
        """
        List the surveys belonging to a user
        If user is admin, he can get surveys of every user (parameter sUser)
        or all surveys (sUser=null). Otherwise, only the surveys belonging to the
        user making the request will be shown.

        Returns a JSON array of surveys containing the following keys:
        sid startdate expires active surveyls_title
        :param username: (optional) Include if you want to limit the scope of the
                         list operation or are only interested in the surveys that
                         belong to you.
        :return: array of survey dict items
        """
        with self.request_ctx("list_surveys"):
            result = self.rpc_proxy.list_surveys(
                sSessionKey=self.session_key, sUser=username or self.username
            )
            return result

    def list_questions(
        self, survey_id: int, group_id: int = None, language: str = None
    ):
        """
        Return the ids and info of (sub-)questions of a survey/group.
        :param survey_id: the survey ID
        :param group_id: (optional) A group ID that can be used for filtering results
        :param language:
        :return: list of questions
        """
        with self.request_ctx("list_questions"):
            result = self.rpc_proxy.list_questions(
                sSessionKey=self.session_key,
                iSurveyID=survey_id,
                iGroupId=group_id,
                sLanguage=language,
            )
            return result

    def get_language_properties(self, survey_id: int):
        """
        Gets language properties
        :param survey_id:
        :return:
        """
        with self.request_ctx("get_language_properties"):
            result = self.rpc_proxy.get_language_properties(
                sSessionKey=self.session_key,
                iSurveyID=survey_id,
                aSurveyLocaleSettings=None,
                sLang=None,
            )
            return result

    def get_survey_properties(self, survey_id: int):
        """
        Retrieves survey properties
        Additional properties (including the survey title)
        must be retrieved from the 'get_language_properties' endpoint

        :param survey_id: the survey ID to retrieve
        :return: list
        """
        with self.request_ctx("get_survey_properties"):
            result = self.rpc_proxy.get_survey_properties(
                sSessionKey=self.session_key,
                iSurveyID=survey_id,
                aSurveyLocaleSettings=None,
                sLang=None,
            )
            return result

    @contextmanager
    def request_ctx(self, endpoint):
        """
        A common helper context that is used for all of the endpoints
        It provides authentication, error handling, logging, and
        stat collection
        :param endpoint:
        :param ctx:
        :return:
        """
        logger.info(f"Sending LimeAPI RPC Request for endpoint [{endpoint}]")
        t0 = pendulum.now()
        try:
            self._validate_auth()
            yield
            duration = (pendulum.now() - t0).total_seconds() * 1000
            logger.info(f"Endpoint [{endpoint}]: Request completed in {duration} ms")
            error = None
        except Exception as e:
            error = e
            traceback.print_exc()

        if error:
            raise error

    def export_responses(
        self,
        survey_id: int,
        language_code: str = None,
        completion_status: str = "all",
        heading_type: str = "code",
        response_type: str = "long",
        from_response_id: int = None,
        to_response_id: int = None,
        fields=None,
    ):
        with self.request_ctx("get_survey_properties"):
            _completion_statuses = ["complete", "incomplete", "all"]
            _heading_types = ["code", "full", "abbreviated"]
            _response_types = ["short", "long"]

            result_b64 = self.rpc_proxy.export_responses(
                sSessionKey=self.session_key,
                iSurveyID=survey_id,
                sDocumentType="json",
                sLanguageCode=language_code,
                sCompletionStatus=completion_status,
                sHeadingType=heading_type,
                sResponseType=response_type,
                iFromResponseID=from_response_id,
                iToResponseID=to_response_id,
                aFields=fields,
            )
            result_utf8 = base64.b64decode(result_b64).decode("utf-8")
            result_json = json.loads(result_utf8)
            result_json = result_json["responses"]
            rows = []
            for id_survey_map in result_json:
                for survey in id_survey_map.values():
                    rows.append(survey)
            return rows

    @staticmethod
    def patch_json_rpc_protocol():
        def parse_reply_patched(self, data):
            """Deserializes and validates a response.

            Called by the client to reconstruct the serialized :py:class:`JSONRPCResponse`.

            :param bytes data: The data stream received by the transport layer containing the
                serialized request.
            :return: A reconstructed response.
            :rtype: :py:class:`JSONRPCSuccessResponse` or :py:class:`JSONRPCErrorResponse`
            :raises InvalidReplyError: if the response is not valid JSON or does not conform
                to the standard.
            """
            if isinstance(data, bytes):
                data = data.decode()
            try:
                print(data)
                rep = json.loads(data)
            except Exception as e:
                traceback.print_exc()
                raise InvalidReplyError(e)
            for k in rep.keys():
                if not k in self._ALLOWED_REPLY_KEYS:
                    raise InvalidReplyError("Key not allowed: %s" % k)
            if "id" not in rep:
                raise InvalidReplyError("Missing id in response")
            if "error" in rep and rep["error"] is not None:
                pprint(rep)
                response = JSONRPCErrorResponse()
                error = rep["error"]
                if isinstance(error, str):
                    response.error = error
                    response.code = -1
                    response._jsonrpc_error_code = -1
                else:
                    response.error = error["message"]
                    response._jsonrpc_error_code = error["code"]
                    if "data" in error:
                        response.data = error["data"]
            else:
                response = JSONRPCSuccessResponse()
                response.result = rep.get("result", None)
            response.unique_id = rep["id"]
            return response

        logger.info("Patching JSONRPCProtocol `parse_reply` method")
        JSONRPCProtocol.parse_reply = parse_reply_patched

    def _validate_settings(self):
        """
        Makes sure that the we instantiated properly
        :return:
        """
        logger.info("Validating LimeAPI settings")
        if None in [self.url, self.username, self.password]:
            raise EnvironmentError()

    def _validate_rpc_resources(self):

        if not isinstance(self.rpc_client, RPCClient):
            return False

        if not isinstance(self.rpc_proxy, RPCProxy):
            return False

        return True

    def _validate_session_key(self):

        if self.session_key is None:
            return False

        if not isinstance(self.session_key, str):
            return False

        if type(self.session_key) is str and len(self.session_key) == 0:
            return False

        return True

    def _validate_auth(self):
        """
        Checks for authentication issues
        :return: None
        """
        # Checking that we ran auth initialization

        if not self._authenticated:
            self.authenticate()

        elif not self._validate_session_key():
            self.authenticate()

        elif not self._validate_rpc_resources():
            self.authenticate()


