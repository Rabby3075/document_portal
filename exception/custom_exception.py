import sys
import traceback
from logger.custom_logger import CustomLogger
logger = CustomLogger().get_logger(__file__)

class DocumentPortalCustomException(Exception):
    def __init__(self, error_message, error_detail=sys):
        super().__init__(str(error_message))
        self.error_message = str(error_message)

        exc_type, exc_value, exc_tb = error_detail.exc_info() if hasattr(error_detail, "exc_info") else (None, None, None)
        if exc_tb is not None:
            # Walk to the deepest frame for the most relevant file/line
            tb = exc_tb
            while tb.tb_next is not None:
                tb = tb.tb_next
            self.file_name = tb.tb_frame.f_code.co_filename
            self.line_number = tb.tb_lineno
            self.traceback_str = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))
        else:
            # Raised cold (no active exception). Fall back to the caller's frame.
            frame = sys._getframe(1)
            self.file_name = frame.f_code.co_filename
            self.line_number = frame.f_lineno
            self.traceback_str = ''.join(traceback.format_stack(frame))
    
    def __str__(self):
        return f"""
            Error in [{self.file_name}] at line [{self.line_number}]
            Error Message: {self.error_message}
            Traceback:
            {self.traceback_str}
        """
# if __name__ == "__main__":
#     try:
#         a = 1 / 0
#         print(a)
#     except Exception as e:
#         custom_exception = CustomException(e, sys)
#         logger.error(custom_exception)
#         raise custom_exception