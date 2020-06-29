from google.oauth2 import service_account
from gspread_pandas import Spread, Client
from loguru import logger


class Workbook:
    """
    Google Cloud config
    """

    def __init__(self, workbook_id, survey, service_account_json_path):
        """
        Initializes Google Cloud configuration
        :param service_account_json_path: filepath containing service account creds
        :param google_drive_api_key: api key used to modify google drive files
        """
        self.workbook_id = workbook_id
        self.survey = survey
        self.service_account_json_path = service_account_json_path

    @property
    def credentials(self):
        """Loads Google service account credentials from a JSON file
        :param google_credentials_json_path: Path to the service account credentials
        :return: A google.oauth2.service_account.Credentials instance
        """
        credentials = service_account.Credentials.from_service_account_file(
            self.service_account_json_path,
            scopes=[
                "https://www.googleapis.com/auth/drive",
                "https://www.googleapis.com/auth/drive.file",
                "https://www.googleapis.com/auth/spreadsheets",
            ],
        )
        return credentials

    def sync(self):
        logger.info(f"Synchronizing Workbook: {self.workbook_id}")

        client = Client(creds=self.credentials)
        spread = Spread(self.workbook_id, create_sheet=True, client=client)

        for sheet_name, data in self.survey.worksheets:
            logger.info(f"Updating Google Sheet: {sheet_name}")
            spread.df_to_sheet(data, index=False, sheet=sheet_name, replace=True)
            logger.success(f"Google Sheet updated: {sheet_name}")

        logger.success(f"Workbook synchronized: {self.workbook_id}")
