import os

class TemplateParser:
    def __init__(self, language:str=None, default_language:str=None):
        self.current_path =os.path.dirname(os.path.abspath(__file__))
        self.language = language
        self.default_language = default_language

        self.set_language(language)


    def set_language(self, language:str):
        if not language:
            self.language = self.default_language

        language_path=os.path.join(self.current_path,"locales",language)

        if os.path.exists(language_path):
            self.language = language
        else:
            self.language = self.default_language


    def get_template_from_locales(self,group:str,key:str,varabels: dict={}):

        if not group or not key:
            return None

        group_path = os.path.join(self.current_path, "locales", self.language, f"{group}.py")
        targeted_language=self.language

        if not os.path.exists(group_path):
            group_path = os.path.join(self.current_path, "locales", self.default_language, f"{group}.py")
            targeted_language=self.default_language

        if not os.path.exists(group_path):
            return None

        # Import group module



        module = __import__(
            f"src.stores.llms.templates.locales.{targeted_language}.{group}",
            fromlist=[group]
        )

        if not module:
            return None

        key_attribute=getattr(module,key)
        return key_attribute.substitute(varabels)

