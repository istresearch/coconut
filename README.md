# coconut

*A LimeSurvey data extractor*

## Installation

```
pip install git+https://github.com/istresearch/coconut
```

## Usage


```python
from coconut import LimeAPI, Survey, Workbook

# Create a LimeAPI instance
lime = LimeAPI(
        url="https://surveys.my-lime-survey-instance.org",
        username="admin",
        password="password"
    )

# Create the survey instance
survey = Survey(survey_id=119618, lime_api=lime)

# Load questions, responses, survey info
survey.load_data()

# Save the data to an Excel file
survey.to_excel("survey.xlsx")

# Save response data to a CSV file
survey.to_csv("survey.csv")

# Update a Google Sheets workbook
workbook = Workbook(
    workbook_id="abc123",
    survey=survey,
    service_account_json_path="google-cloud-creds.json"
)
workbook.sync()
```