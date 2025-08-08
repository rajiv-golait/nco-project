#!/usr/bin/env python3
"""
Process NCO PDF files to extract occupation data for the search system.

This script reads NCO PDF files and extracts:
- NCO Code (XXXX.XXXX format)
- Title (English occupation name)
- Description (detailed job description)
- Synonyms (alternative names in EN/HI)
- Examples (common tasks/activities)
"""

import json
import re
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import logging
from collections import defaultdict

try:
    import pdfplumber
except ImportError:
    print("Error: pdfplumber not installed. Run: pip install pdfplumber")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('pdf_processing.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Regular expressions for parsing
NCO_CODE_PATTERN = re.compile(r'\b(\d{4}\.\d{4})\b')
HINDI_PATTERN = re.compile(r'[\u0900-\u097F]+')  # Devanagari script
TASK_INDICATORS = [
    'performs', 'carries out', 'responsible for', 'duties include',
    'involves', 'operates', 'maintains', 'prepares', 'assists',
    'handles', 'manages', 'supervises', 'inspects', 'repairs'
]


class NCOPDFProcessor:
    """Process NCO PDF files to extract occupation data."""
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.occupations = []
        self.errors = []
        
    def process_all_pdfs(self) -> List[Dict[str, Any]]:
        """Process all PDF files in the data directory."""
        pdf_files = list(self.data_dir.glob("*.pdf"))
        
        if not pdf_files:
            logger.error(f"No PDF files found in {self.data_dir}")
            return []
        
        logger.info(f"Found {len(pdf_files)} PDF files to process")
        
        for pdf_file in pdf_files:
            logger.info(f"Processing: {pdf_file.name}")
            try:
                self._process_single_pdf(pdf_file)
            except Exception as e:
                logger.error(f"Error processing {pdf_file.name}: {str(e)}")
                self.errors.append(f"{pdf_file.name}: {str(e)}")
        
        logger.info(f"Successfully extracted {len(self.occupations)} occupations")
        return self.occupations
    
    def _process_single_pdf(self, pdf_path: Path) -> None:
        """Process a single PDF file."""
        with pdfplumber.open(pdf_path) as pdf:
            current_occupation = None
            
            for page_num, page in enumerate(pdf.pages, 1):
                try:
                    text = page.extract_text()
                    if not text:
                        continue
                    
                    # Process tables if present
                    tables = page.extract_tables()
                    if tables:
                        for table in tables:
                            self._process_table(table)
                    
                    # Process regular text
                    lines = text.split('\n')
                    for i, line in enumerate(lines):
                        line = line.strip()
                        if not line:
                            continue
                        
                        # Check for NCO code
                        code_match = NCO_CODE_PATTERN.search(line)
                        if code_match:
                            # Save previous occupation if exists
                            if current_occupation and self._validate_occupation(current_occupation):
                                self.occupations.append(current_occupation)
                            
                            # Start new occupation
                            current_occupation = {
                                'nco_code': code_match.group(1),
                                'title': '',
                                'description': '',
                                'synonyms': [],
                                'examples': []
                            }
                            
                            # Extract title (usually follows the code)
                            title_text = line[code_match.end():].strip()
                            if not title_text and i + 1 < len(lines):
                                title_text = lines[i + 1].strip()
                            
                            current_occupation['title'] = self._clean_title(title_text)
                        
                        elif current_occupation:
                            # Add to description
                            if self._is_description_line(line):
                                current_occupation['description'] += ' ' + line
                            
                            # Extract synonyms
                            synonyms = self._extract_synonyms(line)
                            if synonyms:
                                current_occupation['synonyms'].extend(synonyms)
                            
                            # Extract examples
                            examples = self._extract_examples(line)
                            if examples:
                                current_occupation['examples'].extend(examples)
                
                except Exception as e:
                    logger.warning(f"Error on page {page_num}: {str(e)}")
            
            # Don't forget the last occupation
            if current_occupation and self._validate_occupation(current_occupation):
                self.occupations.append(current_occupation)
    
    def _process_table(self, table: List[List[str]]) -> None:
        """Process table data to extract occupations."""
        headers = []
        code_col = -1
        title_col = -1
        desc_col = -1
        
        # Identify columns
        if table and len(table) > 0:
            headers = [str(cell).lower() if cell else '' for cell in table[0]]
            
            for i, header in enumerate(headers):
                if 'code' in header or 'nco' in header:
                    code_col = i
                elif 'title' in header or 'occupation' in header:
                    title_col = i
                elif 'description' in header or 'duties' in header:
                    desc_col = i
        
        # Process rows
        for row_idx, row in enumerate(table[1:], 1):
            try:
                if code_col >= 0 and code_col < len(row):
                    code_text = str(row[code_col]) if row[code_col] else ''
                    code_match = NCO_CODE_PATTERN.search(code_text)
                    
                    if code_match:
                        occupation = {
                            'nco_code': code_match.group(1),
                            'title': '',
                            'description': '',
                            'synonyms': [],
                            'examples': []
                        }
                        
                        # Extract title
                        if title_col >= 0 and title_col < len(row):
                            occupation['title'] = self._clean_title(str(row[title_col]))
                        
                        # Extract description
                        if desc_col >= 0 and desc_col < len(row):
                            desc_text = str(row[desc_col]) if row[desc_col] else ''
                            occupation['description'] = self._clean_description(desc_text)
                            occupation['examples'] = self._extract_examples(desc_text)
                        
                        # Extract synonyms from title or other columns
                        for cell in row:
                            if cell:
                                synonyms = self._extract_synonyms(str(cell))
                                if synonyms:
                                    occupation['synonyms'].extend(synonyms)
                        
                        if self._validate_occupation(occupation):
                            self.occupations.append(occupation)
            
            except Exception as e:
                logger.warning(f"Error processing table row {row_idx}: {str(e)}")
    
    def _clean_title(self, title: str) -> str:
        """Clean and normalize occupation title."""
        # Remove NCO code if present
        title = NCO_CODE_PATTERN.sub('', title).strip()
        
        # Remove common prefixes/suffixes
        title = re.sub(r'^(occupation|job|title|:|-|\.|,)+', '', title, flags=re.IGNORECASE).strip()
        title = re.sub(r'(\.|,|-|:)+$', '', title).strip()
        
        # Normalize whitespace
        title = ' '.join(title.split())
        
        # Title case for English parts
        words = title.split()
        cleaned_words = []
        for word in words:
            if not HINDI_PATTERN.search(word) and word.lower() not in ['of', 'and', 'the', 'in', 'for']:
                word = word.capitalize()
            cleaned_words.append(word)
        
        return ' '.join(cleaned_words)
    
    def _clean_description(self, desc: str) -> str:
        """Clean and normalize description text."""
        # Remove extra whitespace
        desc = ' '.join(desc.split())
        
        # Ensure proper sentence ending
        desc = desc.strip()
        if desc and not desc[-1] in '.!?':
            desc += '.'
        
        # Capitalize first letter
        if desc:
            desc = desc[0].upper() + desc[1:]
        
        return desc
    
    def _extract_synonyms(self, text: str) -> List[str]:
        """Extract synonyms from text."""
        synonyms = []
        
        # Common synonym indicators
        synonym_patterns = [
            r'also\s+known\s+as[:\s]+([^.;]+)',
            r'synonyms?[:\s]+([^.;]+)',
            r'alternate\s+names?[:\s]+([^.;]+)',
            r'other\s+names?[:\s]+([^.;]+)',
            r'KATEX_INLINE_OPEN([^)]+)KATEX_INLINE_CLOSE',  # Text in parentheses
            r'/\s*([^/,;.]+)(?=[,;.]|$)'  # Slash-separated alternatives
        ]
        
        for pattern in synonym_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                # Split by common delimiters
                parts = re.split(r'[,;/]', match)
                for part in parts:
                    part = part.strip()
                    if part and len(part) > 2 and part.lower() not in ['etc', 'e.g', 'i.e']:
                        synonyms.append(part)
        
        # Also check for Hindi terms mixed with English
        if HINDI_PATTERN.search(text):
            # Extract Hindi words as potential synonyms
            hindi_words = HINDI_PATTERN.findall(text)
            for word in hindi_words:
                if len(word) > 2:  # Skip very short words
                    synonyms.append(word)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_synonyms = []
        for syn in synonyms:
            syn_lower = syn.lower()
            if syn_lower not in seen:
                seen.add(syn_lower)
                unique_synonyms.append(syn)
        
        return unique_synonyms
    
    def _extract_examples(self, text: str) -> List[str]:
        """Extract example tasks and activities from text."""
        examples = []
        
        # Split into sentences
        sentences = re.split(r'[.!?]+', text)
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            # Check if sentence contains task indicators
            sentence_lower = sentence.lower()
            for indicator in TASK_INDICATORS:
                if indicator in sentence_lower:
                    # Extract the task description
                    task = self._clean_task_description(sentence)
                    if task and len(task) > 10:  # Skip very short tasks
                        examples.append(task)
                    break
        
        # Also look for bullet points or numbered lists
        list_patterns = [
            r'[-•*]\s*([^-•*\n]+)',  # Bullet points
            r'\d+\.\s*([^.\n]+)',     # Numbered lists
            r'[a-z]KATEX_INLINE_CLOSE\s*([^)\n]+)',   # Letter lists
        ]
        
        for pattern in list_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                task = self._clean_task_description(match)
                if task and len(task) > 10:
                    examples.append(task)
        
        # Remove duplicates and limit to reasonable number
        unique_examples = []
        seen = set()
        for ex in examples:
            ex_lower = ex.lower()
            if ex_lower not in seen:
                seen.add(ex_lower)
                unique_examples.append(ex)
        
        return unique_examples[:10]  # Limit to 10 examples
    
    def _clean_task_description(self, task: str) -> str:
        """Clean and format task description."""
        # Remove leading articles
        task = re.sub(r'^(the|a|an)\s+', '', task, flags=re.IGNORECASE).strip()
        
        # Lowercase first letter unless it's a proper noun or acronym
        if task and not task[0].isupper() or (len(task) > 1 and task[1].islower()):
            task = task[0].lower() + task[1:]
        
        # Remove trailing punctuation
        task = re.sub(r'[,;:]+$', '', task).strip()
        
        return task
    
    def _is_description_line(self, line: str) -> bool:
        """Check if a line is likely part of a description."""
        # Skip lines that are likely headers or metadata
        skip_patterns = [
            r'^\d+$',  # Just numbers
            r'^page\s+\d+',  # Page numbers
            r'^chapter|section|unit',  # Headers
            r'^\s*$',  # Empty lines
            r'^={3,}|^-{3,}',  # Separators
        ]
        
        line_lower = line.lower()
        for pattern in skip_patterns:
            if re.match(pattern, line_lower):
                return False
        
        # Must have some substantial content
        return len(line) > 20
    
    def _validate_occupation(self, occupation: Dict[str, Any]) -> bool:
        """Validate occupation data."""
        # Must have code and title
        if not occupation.get('nco_code') or not occupation.get('title'):
            return False
        
        # Code format validation
        if not NCO_CODE_PATTERN.match(occupation['nco_code']):
            logger.warning(f"Invalid NCO code format: {occupation['nco_code']}")
            return False
        
        # Title length validation
        if len(occupation['title']) < 3 or len(occupation['title']) > 200:
            logger.warning(f"Invalid title length for {occupation['nco_code']}: {occupation['title']}")
            return False
        
        # Clean up description
        occupation['description'] = self._clean_description(occupation['description'])
        
        # Remove duplicate synonyms
        occupation['synonyms'] = list(dict.fromkeys(occupation['synonyms']))
        
        # Remove duplicate examples
        occupation['examples'] = list(dict.fromkeys(occupation['examples']))
        
        return True
    
    def save_to_json(self, output_path: Path) -> None:
        """Save extracted occupations to JSON file."""
        # Sort by NCO code
        self.occupations.sort(key=lambda x: x['nco_code'])
        
        # Remove any duplicates
        seen_codes = set()
        unique_occupations = []
        for occ in self.occupations:
            if occ['nco_code'] not in seen_codes:
                seen_codes.add(occ['nco_code'])
                unique_occupations.append(occ)
            else:
                logger.warning(f"Duplicate NCO code found: {occ['nco_code']}")
        
        # Write to file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(unique_occupations, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Saved {len(unique_occupations)} occupations to {output_path}")
        
        # Write summary statistics
        self._print_statistics(unique_occupations)
    
    def _print_statistics(self, occupations: List[Dict[str, Any]]) -> None:
        """Print summary statistics."""
        total = len(occupations)
        with_desc = sum(1 for o in occupations if o['description'])
        with_syn = sum(1 for o in occupations if o['synonyms'])
        with_ex = sum(1 for o in occupations if o['examples'])
        
        avg_syn = sum(len(o['synonyms']) for o in occupations) / total if total > 0 else 0
        avg_ex = sum(len(o['examples']) for o in occupations) / total if total > 0 else 0
        
        print("\n" + "="*50)
        print("EXTRACTION SUMMARY")
        print("="*50)
        print(f"Total occupations: {total}")
        print(f"With descriptions: {with_desc} ({with_desc/total*100:.1f}%)")
        print(f"With synonyms: {with_syn} ({with_syn/total*100:.1f}%)")
        print(f"With examples: {with_ex} ({with_ex/total*100:.1f}%)")
        print(f"Average synonyms per occupation: {avg_syn:.1f}")
        print(f"Average examples per occupation: {avg_ex:.1f}")
        
        if self.errors:
            print(f"\nErrors encountered: {len(self.errors)}")
            for error in self.errors[:5]:  # Show first 5 errors
                print(f"  - {error}")
        
        print("="*50 + "\n")


def main():
    """Main entry point."""
    # Setup paths
    script_dir = Path(__file__).parent
    data_dir = script_dir  # PDFs are in the same directory as this script
    output_path = script_dir.parent / 'nco_data.json'
    
    logger.info("Starting NCO PDF processing...")
    
    # Check for PDF files
    pdf_files = list(data_dir.glob("*.pdf"))
    if not pdf_files:
        logger.error(f"No PDF files found in {data_dir}")
        logger.info("Please add NCO PDF files to the data/ directory")
        sys.exit(1)
    
    logger.info(f"Found PDF files: {[f.name for f in pdf_files]}")
    
    # Process PDFs
    processor = NCOPDFProcessor(data_dir)
    occupations = processor.process_all_pdfs()
    
    if not occupations:
        logger.error("No occupations extracted from PDFs")
        sys.exit(1)
    
    # Save to JSON
    processor.save_to_json(output_path)
    
    # Create sample file if needed
    sample_path = script_dir.parent / 'nco_data.sample.json'
    if not sample_path.exists():
        # Take first 20 occupations as sample
        sample_data = occupations[:20]
        with open(sample_path, 'w', encoding='utf-8') as f:
            json.dump(sample_data, f, ensure_ascii=False, indent=2)
        logger.info(f"Created sample file with {len(sample_data)} occupations")
    
    logger.info("PDF processing completed successfully!")
    
    # Print final message
    print("\nNext steps:")
    print("1. Review the generated nco_data.json file")
    print("2. Run 'python embeddings/build_index.py' to build the search index")
    print("3. Start the backend server to test search functionality")


if __name__ == "__main__":
    main()