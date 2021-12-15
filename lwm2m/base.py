from aiocoap.resource import ObservableResource

class LwM2MBase(ObservableResource):
    """Base class for all LwM2M objects and resources"""

    def __init__(self, desc = ''):
        self.desc = desc

    def get_desc(self):
        return self.desc
