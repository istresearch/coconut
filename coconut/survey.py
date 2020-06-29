import os

import pandas as pd
from loguru import logger

from coconut.lime import LimeAPI
from coconut.question import Question, QuestionGroup
from coconut.response import Response
from coconut.utils import get_col_widths, classproperty, dump_yaml
from typing import List, Tuple


class Survey:
    """Represents a Lime Survey"""

    @classproperty
    def response_cls(cls):
        """The class used to load responses.
        By default, the base Response class is used. This Response class can be
        extended to define survey-specific property accessors, output schemas, etc.
        """
        return Response

    def __init__(self, survey_id, lime_api: LimeAPI, workbook_id=None, title=None):
        """Instantiates a Survey instance
        :param survey_id: LimeSurvey survey ID
        :param lime_api: LimeSurvey API instance
        """
        self._title = title
        self.survey_id = survey_id
        self.lime_api = lime_api
        self.workbook_id = workbook_id
        self.questions_by_id = None
        self.questions_by_title = None
        self.question_groups_by_key = None
        self.responses_by_id = None
        self.language_props = None
        self.survey_props = None

    def __len__(self):
        """Number of responses available for this survey"""
        assert (
            self.responses_by_id is not None
        ), "Unable to determine survey size. Responses have not been loaded."
        return len(self.responses_by_id)

    @property
    def id(self):
        """Survey ID"""
        return self.survey_id

    @property
    def title(self):
        """Survey Title"""
        if self._title is None:
            try:
                self.survey_props["surveyls_title"]
            except:
                return f'Survey {self.survey_id}'
        else:
            return self._title
        return f"Survey"


    @property
    def worksheets(self) -> List[Tuple[str, pd.DataFrame]]:
        return [
            ("Responses", self._response_dataframe()),
            ("Questions", self._question_dataframe()),
            ("Question Groups", self._question_group_dataframe())
        ]

    @property
    def dataframe(self):
        return self._response_dataframe()


    def load_data(self):
        """Loads data from LimeSurvey"""
        logger.info(f"[{self.id}] Loading data")
        self._initialize_api()
        self._load_survey_props()
        self._load_language_props()
        self._load_questions()
        self._load_responses()

    def to_excel(self, filepath):
        """Saves data"""
        logger.info(f"[{self.id}] Saving data")
        self._save_workbook(filepath)

    def to_csv(self, filepath, **kwargs):
        self.dataframe.to_csv(filepath, **kwargs)


    def _initialize_api(self):
        """Initializes the LimeSurvey API"""
        logger.info(f"[{self.id}] Authenticating Lime API Client")
        self.lime_api.authenticate()

    def _load_language_props(self):
        """Loads language properties from LimeSurvey"""
        logger.info(f"[{self.id}] Loading language props")
        self.language_properties = self.lime_api.get_language_properties(self.id)

    def _load_survey_props(self):
        """Loads survey properties from LimeSurvey"""
        logger.info(f"[{self.id}] Loading survey props")
        self.survey_props = self.lime_api.get_survey_properties(self.id)

    def _load_responses(self):
        """Loads response data from LimeSurvey"""
        logger.info(f"[{self.id}] Loading responses")
        self.responses_by_id = {}
        for r in self.lime_api.export_responses(self.survey_id):
            response = self.response_cls(r)
            self.responses_by_id[response.id] = response

    def _load_questions(self):
        """Loads survey question information from LimeSurvey"""
        logger.info(f"[{self.id}] Loading questions")
        self.questions_by_id = {}
        for q in self.lime_api.list_questions(self.id):
            question = Question(q)
            self.questions_by_id[question.question_id] = question
        self._process_question_relationships()
        self._create_question_title_mapping()

    def _process_question_relationships(self):
        """Creates parent-child relationships between related questions
        Allows us to link questions directly to response items via question title
        """
        self.question_groups_by_key = {}
        for q in self.questions_by_id.values():
            if q.parent_qid in self.questions_by_id:
                parent = self.questions_by_id[q.parent_qid]
                self._create_question_link(parent, q)
                self._create_question_group(parent)

    def _create_question_title_mapping(self):
        """Maps question title to question objects
        Requires question relationships to be processed beforehand, because
        title is dependent on whether or not the question has a parent, indicating
        it's part of another question.
        """
        self.questions_by_title = {}
        for q in self.questions_by_id.values():
            self.questions_by_title[q.title] = q

    def _create_question_link(self, parent, child):
        """Creates a link between parent-child question pairs"""
        child.link_parent(parent)

    def _create_question_group(self, q: Question):
        """Creates a question group if one doesn't exist for the question
        :param q: a question with child nodes
        """
        if q.title not in self.question_groups_by_key:
            logger.info(f"Creating question group: {q.title}")
            group = QuestionGroup(parent=q)
            self.question_groups_by_key[group.key] = group

    def _question_dataframe(self):
        """Creates a dataframe containing information about each survey question"""
        questions = list(self.questions_by_title.values())
        questions = sorted(questions, key=lambda x: x.title)
        questions = [q.dict() for q in questions]
        return pd.DataFrame(questions, columns=Question._columns)

    def _question_group_dataframe(self):
        """Creates a dataframe containing information about each survey question"""
        question_groups = list(self.question_groups_by_key.values())
        question_groups = sorted(question_groups, key=lambda x: x.key)
        question_groups = [qg.dict(flattened=True) for qg in question_groups]
        return pd.DataFrame(question_groups, columns=QuestionGroup._columns)

    def _response_dataframe(self):
        """Creates a dataframe containing information about each survey question"""
        responses = list(self.responses_by_id.values())
        responses = sorted(responses, key=lambda x: x.id)
        responses = [r.dict() for r in responses]
        return pd.DataFrame(responses)

    def _save_workbook(self, filepath):
        logger.info(f"[{self.id}] Saving workbook to {filepath}")
        writer = pd.ExcelWriter(filepath, engine="xlsxwriter")
        for sheet_name, data in self.worksheets:
            self._add_worksheet(writer, data, sheet_name)
        writer.save()
        logger.success(f"[{self.id}] Workbook saved to {filepath}")

    def _add_worksheet(self, writer, dataframe, sheet_name):
        logger.info(f"[{self.id}] Adding worksheet: {sheet_name}")
        dataframe.to_excel(writer, sheet_name=sheet_name)
        for i, width in enumerate(get_col_widths(dataframe)):
            writer.sheets[sheet_name].set_column(i, i, min(30, width * 1.25))


    @property
    def basename(self):
        """File basename"""
        return f"{self.id}-{self.title.replace(' ', '-')}"

    def _save_survey_properties(self, data_dir):
        """Saves survey information"""
        dump_yaml(self.language_props, os.path.join(data_dir, "survey-info.yml"))

    def _save_language_properties(self, data_dir):
        """Saves language information"""
        dump_yaml(self.language_props, os.path.join(data_dir, "language-info.yml"))
