import json
import os
from utils.helper import init_logger
from settings import CopilotSettings  

config = CopilotSettings()
# Logger initialization
logger = init_logger(config.LOG_PATH)

class JSONHandler:  
    def __init__(
            self, 
            id: str, 
            json_data_dir: str
        ):  
        self.id = id  
        self.json_data_dir = json_data_dir  
  
    def check_and_create_json_dir(self):
        if not os.path.exists(self.json_data_dir):  
            logger.error("JSON directory does not exist!")  
            logger.info("Creating new JSON directory...")  
            os.makedirs(self.json_data_dir)
            logger.info("New JSON directory created!")
  
    def json_exists(self):  
        json_ids = [json_id.replace(".json", "") for json_id in os.listdir(self.json_data_dir)]  
        return self.id in json_ids  
  
    def save_json(self, content):  
        json_data_path = os.path.join(self.json_data_dir, f"{self.id}.json")  
        with open(json_data_path, 'w') as f:  
            json.dump(content, f)  
  
    def load_json(self):  
        json_data_path = os.path.join(self.json_data_dir, f"{self.id}.json")  
        with open(json_data_path, 'r') as f:  
            return json.load(f)  