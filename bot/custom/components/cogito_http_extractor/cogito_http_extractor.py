import time
import json
import logging
import os
import requests
from typing import Any, List, Optional, Text, Dict, Tuple

from rasa.constants import DOCS_URL_COMPONENTS
from rasa.nlu.constants import ENTITIES
from rasa.nlu.config import RasaNLUModelConfig
from rasa.nlu.extractors.extractor import EntityExtractor
from rasa.nlu.model import Metadata
from rasa.nlu.training_data import Message
from rasa.utils.common import raise_warning

logger = logging.getLogger(__name__)

def convert_cogito_format_to_rasa(
    api_response: Dict[Text, Any]
) -> List[Dict[Text, Any]]:
    extracted = []


    if api_response == {}:
        return extracted
    else:
        for api_entity in api_response['data']['entities']:
            for position in api_entity['positions']:
                entity = {
                    "start": position["start"],
                    "end": position["end"],
                    "text": api_response['data'].get("content", None).rstrip(), # see if is needed
                    "value": api_entity['lemma'],
                    "confidence": 1.0,
                    "syncon": api_entity['syncon'],
                    "entity": api_entity["type"],
                }
                extracted.append(entity)

        return extracted

class CogitoHTTPExtractor(EntityExtractor):
    """ Searches for structured entities using the Cogito API by Expert Systems. """

    # to be populated with default values to be passed to Cogito API request
    defaults = {
    'url': 'https://cogitoapi.io/nlu/v1/api/emotion/analysis/entities',
    'token': 'eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6IlJFTTFSamt5UlVZNU5FUTBOalk0TmtJMU9UZzBOelpHUTBFM1FVWkNRVUUxTWtJek0wWXpPQSJ9.eyJpc3MiOiJodHRwczovL2NvZ2l0b2Nsb3VkLmF1dGgwLmNvbS8iLCJzdWIiOiJjUlBlM3E5bml4c2YwMWFVOGY5ZEluOVBzeE9ueDk2N0BjbGllbnRzIiwiYXVkIjoiY29naXRvLWNsb3VkIiwiaWF0IjoxNTkzNTMzODQ1LCJleHAiOjE1OTM2MjAyNDUsImF6cCI6ImNSUGUzcTluaXhzZjAxYVU4ZjlkSW45UHN4T254OTY3IiwiZ3R5IjoiY2xpZW50LWNyZWRlbnRpYWxzIn0.X82u_Gz1b5o5b0xVK7j8FaCxVpWiZIt3mI1iqe1RBs2rPgrmuM8SzBq_yUxdV-uDZj9vK8v20X_vN3bqpTWWC-nvvF7VDNZlaaszVDPANZchvxRZBEloJj7ECtMyx1j0FMtpFIKF7q3hlfk4U6Pu34cErqNeLg4dFDO_w89j2b-8tgGefjsiMliZaAmT_R1MDaBQN0Kupy-ewES03QJ_qzYhg9UBzSgQkH_cIDIleQCZ3FcLVQq54HWhL4OGbuOSAlqBE8W0jPtEIn03XxYCpR7BhHKmsAVuGg6TFYjYoAhn_GPbTaV1TIFkF0QkRfuHcLLZfXTuTRAlrbDIICZ7qw'
    }

    def __init__(
        self,
        component_config: Optional[Dict[Text, Any]] = None,
        language: Optional[Text] = None,
    ) -> None:

        super().__init__(component_config)
        self.language = language

    @classmethod
    def create(
        cls, component_config: Dict[Text, Any], config: RasaNLUModelConfig
    ) -> "CogitoHTTPExtractor":
        return cls(component_config, config.language)

    def _url(self) -> Optional[Text]:
        """Return url of the Cogito service. Environment var will override."""
        # if os.environ.get("RASA_DUCKLING_HTTP_URL"):
        #     return os.environ["RASA_DUCKLING_HTTP_URL"]

        return self.component_config.get("url")

    def _token(self) -> Optional[Text]:
        """Return token of the Cogito service. Environment var will override."""
        # if os.environ.get("RASA_DUCKLING_HTTP_URL"):
        #     return os.environ["RASA_DUCKLING_HTTP_URL"]

        return self.component_config.get("token")

    def _data_json(self, text: Text) -> Dict[Text, Any]:
        return {
            "document":{
                "text": text
            }
        }

    def _cogito_request(self, text: Text) -> Dict[Text, Any]:
        """Sends the request to the duckling server."""

        try:
            data_json = self._data_json(text)
            headers = {
                "Content-Type": 'application/json',
                "Authorization": 'Bearer '+self._token()
            }
            params = (
                ('language', self.language),
            )

            response = requests.post(
                url = self._url(),
                headers = headers,
                params = params,
                json = data_json
            )

            # token_good = 'eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6IlJFTTFSamt5UlVZNU5FUTBOalk0TmtJMU9UZzBOelpHUTBFM1FVWkNRVUUxTWtJek0wWXpPQSJ9.eyJpc3MiOiJodHRwczovL2NvZ2l0b2Nsb3VkLmF1dGgwLmNvbS8iLCJzdWIiOiJjUlBlM3E5bml4c2YwMWFVOGY5ZEluOVBzeE9ueDk2N0BjbGllbnRzIiwiYXVkIjoiY29naXRvLWNsb3VkIiwiaWF0IjoxNTkzNTMzODQ1LCJleHAiOjE1OTM2MjAyNDUsImF6cCI6ImNSUGUzcTluaXhzZjAxYVU4ZjlkSW45UHN4T254OTY3IiwiZ3R5IjoiY2xpZW50LWNyZWRlbnRpYWxzIn0.X82u_Gz1b5o5b0xVK7j8FaCxVpWiZIt3mI1iqe1RBs2rPgrmuM8SzBq_yUxdV-uDZj9vK8v20X_vN3bqpTWWC-nvvF7VDNZlaaszVDPANZchvxRZBEloJj7ECtMyx1j0FMtpFIKF7q3hlfk4U6Pu34cErqNeLg4dFDO_w89j2b-8tgGefjsiMliZaAmT_R1MDaBQN0Kupy-ewES03QJ_qzYhg9UBzSgQkH_cIDIleQCZ3FcLVQq54HWhL4OGbuOSAlqBE8W0jPtEIn03XxYCpR7BhHKmsAVuGg6TFYjYoAhn_GPbTaV1TIFkF0QkRfuHcLLZfXTuTRAlrbDIICZ7qw'
            # headers_good = {
            #     'Content-Type': 'application/json',
            #     'Authorization': 'Bearer '+token_good,
            # }

            # params_good = (
            #     ('language', 'en'),
            # )

            # data = {"document": {"text": "Michael Jordan was one of the greatest basketball players of all time. Scoring was Jordan stand-out skill, but he still holds a defensive NBA record, with eight steals in a half."}}

          
            # print("headers\n")
            # print("header: ", headers)
            # print("header_good: ", headers_good)
            
            # print("parameters\n")
            # print("parameter: ", params)
            # print("parameter_good: ", params_good)
            
            # print("data\n")
            # print("data: ", data_json)
            # print("data_good: ", data)

            # response = requests.post(url='https://cogitoapi.io/nlu/v1/api/emotion/analysis/entities', headers=headers, params=params, json=data)



            if response.status_code == 200:
                return response.json()
            else:
                logger.error(
                    "Failed to get a proper response from remote "
                    "cogito API. Status Code: {}. Response: {}"
                    "".format(response.status_code, response.text)
                )
                return {}
        except (
            requests.exceptions.ConnectionError,
            requests.exceptions.ReadTimeout,
        ) as e:
            logger.error(
                "Failed to connect to duckling http server. Make sure "
                "the duckling server is running/healthy/not stale and the proper host "
                "and port are set in the configuration. More "
                "information on how to run the server can be found on "
                "github: "
                "https://github.com/facebook/duckling#quickstart "
                "Error: {}".format(e)
            )
            return {}

    def process(self, message: Message, **kwargs: Any) -> None:

        if self._url() is not None:
            api_response = self._cogito_request(message.text)
            all_extracted = convert_cogito_format_to_rasa(api_response)
            # extracted = DucklingHTTPExtractor.filter_irrelevant_entities(
            #     all_extracted, dimensions
            # )
            extracted = all_extracted
        else:
            extracted = []
            raise_warning(
                "Cogito HTTP component in pipeline, but no "
                "`url` configuration in the config "
                "file nor is `RASA_DUCKLING_HTTP_URL` "
                "set as an environment variable. No entities will be extracted!",
                docs=DOCS_URL_COMPONENTS + "#ducklinghttpextractor",
            )

        extracted = self.add_extractor_name(extracted)
        message.set(ENTITIES, message.get(ENTITIES, []) + extracted, add_to_output=True)

    @classmethod
    def load(
        cls,
        meta: Dict[Text, Any],
        model_dir: Text = None,
        model_metadata: Optional[Metadata] = None,
        cached_component: Optional["CogitoHTTPExtractor"] = None,
        **kwargs: Any,
    ) -> "CogitoHTTPExtractor":

        language = model_metadata.get("language") if model_metadata else None
        return cls(meta, language)