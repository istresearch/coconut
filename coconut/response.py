
class Response:
    """Represents a single survey response"""

    def __init__(self, data: dict):
        """
        Instantiates the response object
        :param data: Response data
        """
        self.data = data

    @property
    def id(self):
        """Response ID
        """
        return self.data['id']

    def dict(self):
        """
        A dictionary containing response data
        :return:
        """
        return self.data