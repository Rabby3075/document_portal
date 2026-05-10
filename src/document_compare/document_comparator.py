import sys
from dotenv import load_dotenv
from logger.custom_logger import CustomLogger
from exception.custom_exception import DocumentPortalCustomException
import pandas as pd
from model.models import SummaryResponse,PromptTypes
from prompt.prompt_library import PROMPT_REGISTRY
from utils.model_loader import ModelLoader
from langchain_core.output_parsers import JsonOutputParser
from langchain.output_parsers import OutputFixingParser
from langchain_text_splitters import RecursiveCharacterTextSplitter

class DocumentComparatorLLM:
    MAX_COMPARE_CHARS = 22000
    CHUNK_SIZE = 11000
    CHUNK_OVERLAP = 800

    def __init__(self):
        load_dotenv()
        self.log = CustomLogger().get_logger(__name__)
        self.loader = ModelLoader()
        self.llm = self.loader.load_llm()
        self.parser = JsonOutputParser(pydantic_object=SummaryResponse)
        self.fixing_parser = OutputFixingParser.from_llm(parser = self.parser, llm = self.llm)
        self.prompt = PROMPT_REGISTRY[PromptTypes.DOCUMENT_COMPARISON.value]
        self.chain = self.prompt | self.llm | self.fixing_parser

    def compare_document(self, combined_docs)->pd.DataFrame:
        try:
            if isinstance(combined_docs, list):
                return self._compare_page_batches(combined_docs)

            if len(combined_docs) <= self.MAX_COMPARE_CHARS:
                response = self._compare_text(combined_docs)
                return self._formate_response(response)

            self.log.info("Combined document text is large, comparing text chunks", characters=len(combined_docs))
            responses = []
            for index, chunk in enumerate(self._chunk_text(combined_docs), start=1):
                chunk_input = f"Section {index} from the combined documents:\n{chunk}"
                responses.extend(self._normalize_response(self._compare_text(chunk_input)))

            self.log.info("Chunked document comparison completed successfully", rows=len(responses))
            return self._formate_response(responses)
        except Exception as e:
            self.log.error("Document comparison failed", error=str(e))
            raise DocumentPortalCustomException("Document comparison failed",sys) from e

    def _compare_text(self, combined_docs: str):
        inputs = {
            "combined_docs": combined_docs,
            "format_instruction": self.parser.get_format_instructions()
        }
        self.log.info("Starting document comparison", characters=len(combined_docs))
        response = self.chain.invoke(inputs)
        self.log.info("Document comparison completed successfully")
        return response

    def _compare_page_batches(self, documents: list[dict])->pd.DataFrame:
        reference_doc, actual_doc = documents
        reference_pages = reference_doc["pages"]
        actual_pages = actual_doc["pages"]
        max_pages = max(len(reference_pages), len(actual_pages))

        batches = []
        current_batch = []
        current_size = 0

        for page_number in range(1, max_pages + 1):
            reference_text = self._get_page_text(reference_pages, page_number)
            actual_text = self._get_page_text(actual_pages, page_number)
            page_block = f"""
Page {page_number}

V1 ({reference_doc['filename']}):
{reference_text or '[Page missing or no extractable text]'}

V2 ({actual_doc['filename']}):
{actual_text or '[Page missing or no extractable text]'}
"""
            page_size = len(page_block)
            if current_batch and current_size + page_size > self.MAX_COMPARE_CHARS:
                batches.append("\n".join(current_batch))
                current_batch = []
                current_size = 0

            if page_size > self.MAX_COMPARE_CHARS:
                page_chunks = self._split_large_page(page_number, reference_doc, actual_doc, reference_text, actual_text)
                batches.extend(page_chunks)
                continue

            current_batch.append(page_block)
            current_size += page_size

        if current_batch:
            batches.append("\n".join(current_batch))

        responses = []
        self.log.info("Starting page-batched comparison", batches=len(batches), pages=max_pages)
        for index, batch in enumerate(batches, start=1):
            batch_input = f"Compare this page batch {index} of {len(batches)}:\n{batch}"
            responses.extend(self._normalize_response(self._compare_text(batch_input)))

        self.log.info("Page-batched comparison completed successfully", rows=len(responses))
        return self._formate_response(responses)

    def _get_page_text(self, pages: list[dict], page_number: int) -> str:
        if page_number > len(pages):
            return ""
        return pages[page_number - 1].get("text", "")

    def _split_large_page(self, page_number: int, reference_doc: dict, actual_doc: dict, reference_text: str, actual_text: str) -> list[str]:
        reference_chunks = self._chunk_text(reference_text)
        actual_chunks = self._chunk_text(actual_text)
        max_chunks = max(len(reference_chunks), len(actual_chunks))
        page_batches = []

        for index in range(max_chunks):
            page_batches.append(f"""
Page {page_number}, part {index + 1}

V1 ({reference_doc['filename']}):
{reference_chunks[index] if index < len(reference_chunks) else '[No matching text part]'}

V2 ({actual_doc['filename']}):
{actual_chunks[index] if index < len(actual_chunks) else '[No matching text part]'}
""")

        return page_batches

    def _chunk_text(self, text: str) -> list[str]:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.CHUNK_SIZE,
            chunk_overlap=self.CHUNK_OVERLAP
        )
        return splitter.split_text(text or "")

    def _normalize_response(self, response)->list[dict]:
        if hasattr(response, "model_dump"):
            response = response.model_dump()

        if isinstance(response, dict) and "root" in response:
            response = response["root"]

        if isinstance(response, list):
            return response

        return [response]

    def _formate_response(self, response)->pd.DataFrame:
        try:
            response = self._normalize_response(response)
            df = pd.DataFrame(response)
            self.log.info("Formating response into DataFrame", dataframe = df)
            return df
        except Exception as e:
            self.log.error("Response formating failed", error=str(e))
            raise DocumentPortalCustomException("Response formating failed",sys) from e
