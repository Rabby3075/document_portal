import sys
import traceback
from logger.custom_logger import CustomLogger
logger = CustomLogger().get_logger(__file__)

class CustomException(Exception):
    def __init__(self, error_message, error_detail: sys):
        _, _, exc_tb = error_detail.exc_info()
        self.file_name = exc_tb.tb_frame.f_code.co_filename
        self.line_number = exc_tb.tb_lineno
        self.error_message = str(error_message)
        self.traceback_str = ''.join(traceback.format_exception(*error_detail.exc_info()))
    
    def __str__(self):
        return f"""
            Error in [{self.file_name}] at line [{self.line_number}]
            Error Message: {self.error_message}
            Traceback:
            {self.traceback_str}
        """
if __name__ == "__main__":
    try:
        a = 1 / 0
        print(a)
    except Exception as e:
        custom_exception = CustomException(e, sys)
        logger.error(custom_exception)
        raise custom_exception