import re


class Question:
    """Represents a survey question"""
    _columns = ("qid", "sid", "gid", "type", "title", "text")

    def __init__(self, data):
        self.data = data
        self.parent = None
        self.children = {}

    def __str__(self):
        return f'Question(id={self.question_id}, title={self.title})'

    def link_child(self, child: 'Question'):
        self.children[child.question_id] = child
        child.parent = self

    def link_parent(self, parent: 'Question'):
        self.parent = parent
        parent.link_child(self)

    @property
    def has_children(self):
        return len(self.children) > 0

    @property
    def is_child(self):
        return self.parent is not None

    @property
    def title(self):
        if self.is_child:
            return f"{self.parent._title}[{self._title}]"
        return self._title

    @property
    def _title(self):
        return self.data["title"]

    @property
    def type(self):
        return self.data["type"]

    @property
    def text(self):
        return clean_question_text(self.data["question"])

    @property
    def survey_id(self):
        return int(self.data["sid"])

    @property
    def group_id(self):
        return int(self.data["gid"])

    @property
    def question_id(self):
        return int(self.data["id"]["qid"])

    @property
    def parent_qid(self):
        return int(self.data["parent_qid"])

    def dict(self):
        return {
            "title": self.title,
            "qid": self.question_id,
            "sid": self.survey_id,
            "gid": self.group_id,
            "type": self.type,
            "text": self.text,
        }


class QuestionGroup:

    _columns = ("key", "question", "options")
    def __init__(self, parent):
        self.parent = parent

    def __str__(self):
        return f"QuestionGroup({self.key})"

    def dict(self, flattened=False):
        res = {
            "key": self.key,
            "question": self.question_text,
            "options": {k: v.text for k, v in self.child_items.items()},
        }
        if flattened:
            res["options"] = "\n".join(
                [
                    f"{q.title}) {q.text}"
                    for q in sorted(self.child_items.values(), key=lambda x: x.title)
                ]
            )
        return res

    @property
    def question_text(self):
        return self.parent.text

    @property
    def child_items(self):
        return self.parent.children

    @property
    def key(self):
        return self.parent.title

    def get_value(self, response):
        response_values = []
        for sq in self.child_items.values():
            answer = response.get_answer(sq)
            if answer == "N/A":
                pass
            else:
                response_values.append(sq.text)
        other_value = self.get_other_value(response)
        response_values = sorted(response_values)
        if other_value is not None:
            response_values.append(other_value)
        return response_values

    def get_other_value(self, response):
        try:
            value = response.get_answer(self.parent.title + "[other]")
            if value == "None":
                return None
            return value
        except KeyError:
            return None


def clean_question_text(text):
    t = text
    t = re.sub(r"[\n\t\r]", " ", t)
    t = re.sub(r"<.*>", " ", t)
    t = re.sub(r" +", " ", t)
    return t
