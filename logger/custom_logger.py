import logging
import os 
from datetime import datetime
class CustomLogger:
    def __init__(self,):
        #ensure logs directory exists
        self.logs_dir = os.path.join(os.getcwd(), "logs")
        os.makedirs("logs", exist_ok=True)

        #create timestamped log file name
        log_file = f"{datetime.now().strftime('%d-%m-%Y_%H_%M_%S')}.log"
        Log_file_path = os.path.join(self.logs_dir, log_file)

        #configure logging
        logging.basicConfig(
            filename=Log_file_path,
            level=logging.INFO,
            format="[%(asctime)s] %(levelname)s %(name)s (line %(lineno)d): %(message)s",
        )
    def get_logger(self,name= __file__ ):
        return logging.getLogger(os.path.basename(name))

if __name__ == "__main__":
    logger = CustomLogger()
    logger = logger.get_logger(__file__)
    logger.info("This is an info log message.")