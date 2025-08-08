#!/usr/bin/env python3
"""
Enhanced NCO Data Processor - High Accuracy Semantic Search Enhancement

This script processes extracted NCO data to add comprehensive semantic search features
with improved accuracy and robustness for AI-enabled occupation matching.

Features:
- Advanced synonym generation with contextual understanding
- Intelligent task example extraction from descriptions
- Multi-level hierarchical classification
- Quality scoring with multiple dimensions
- Multilingual support (English/Hindi)
- Robust error handling and validation

Author: Enhanced Version
Date: 2025-08-08
Version: 2.0
"""

import json
import re
import logging
from pathlib import Path
from typing import List, Dict, Set, Tuple, Optional
from collections import defaultdict, Counter
from dataclasses import dataclass, field
import unicodedata

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('enhancement.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class OccupationHierarchy:
    """Structured hierarchy information"""
    division: str
    division_name: str
    sub_division: str
    major_group: str
    sub_major_group: str
    minor_group: str
    unit_group: str
    skill_level: str
    skill_specialization: str
    
    def to_dict(self) -> Dict:
        return {
            'division': self.division,
            'division_name': self.division_name,
            'sub_division': self.sub_division,
            'major_group': self.major_group,
            'sub_major_group': self.sub_major_group,
            'minor_group': self.minor_group,
            'unit_group': self.unit_group,
            'skill_level': self.skill_level,
            'skill_specialization': self.skill_specialization
        }

class NCOEnhancer:
    """Main processor class for enhancing NCO data"""
    
    def __init__(self):
        self.stats = defaultdict(int)
        self._load_reference_data()
        self._compile_patterns()
        
    def _load_reference_data(self):
        """Load reference data for accurate mapping"""
        # NCO Division mapping
        self.division_mapping = {
            '1': {'name': 'Managers', 'skill_level': 'Skill Level 3-4'},
            '2': {'name': 'Professionals', 'skill_level': 'Skill Level 4'},
            '3': {'name': 'Technicians and Associate Professionals', 'skill_level': 'Skill Level 3'},
            '4': {'name': 'Clerical Support Workers', 'skill_level': 'Skill Level 2'},
            '5': {'name': 'Service and Sales Workers', 'skill_level': 'Skill Level 2'},
            '6': {'name': 'Skilled Agricultural, Forestry and Fishery Workers', 'skill_level': 'Skill Level 2'},
            '7': {'name': 'Craft and Related Trades Workers', 'skill_level': 'Skill Level 2'},
            '8': {'name': 'Plant and Machine Operators and Assemblers', 'skill_level': 'Skill Level 2'},
            '9': {'name': 'Elementary Occupations', 'skill_level': 'Skill Level 1'},
            '0': {'name': 'Armed Forces Occupations', 'skill_level': 'Skill Level 1-4'}
        }
        
        # Occupation base terms for synonym generation
        self.occupation_bases = {
            'worker', 'operator', 'technician', 'specialist', 'assistant',
            'supervisor', 'manager', 'officer', 'executive', 'engineer',
            'maker', 'repairer', 'installer', 'fitter', 'mechanic',
            'clerk', 'secretary', 'administrator', 'coordinator', 'analyst',
            'consultant', 'advisor', 'expert', 'professional', 'practitioner',
            'craftsman', 'artisan', 'journeyman', 'apprentice', 'helper',
            'driver', 'pilot', 'captain', 'conductor', 'attendant'
        }
        
        # Industry-specific terms
        self.industry_terms = {
            'technology': {'IT', 'software', 'hardware', 'computer', 'digital', 'cyber', 'tech', 'system', 'network', 'database'},
            'healthcare': {'medical', 'health', 'clinical', 'patient', 'hospital', 'nursing', 'therapeutic', 'diagnostic', 'pharmaceutical'},
            'manufacturing': {'factory', 'production', 'assembly', 'industrial', 'machinery', 'equipment', 'processing', 'fabrication'},
            'construction': {'building', 'construction', 'civil', 'structural', 'infrastructure', 'architectural', 'engineering'},
            'education': {'teaching', 'academic', 'educational', 'training', 'instruction', 'learning', 'school', 'university'},
            'finance': {'financial', 'banking', 'accounting', 'investment', 'insurance', 'fiscal', 'monetary', 'economic'},
            'agriculture': {'farming', 'agricultural', 'crop', 'livestock', 'horticulture', 'fishery', 'forestry', 'plantation'},
            'transport': {'transportation', 'logistics', 'shipping', 'freight', 'cargo', 'delivery', 'aviation', 'maritime'},
            'hospitality': {'hotel', 'restaurant', 'catering', 'tourism', 'hospitality', 'food service', 'accommodation'},
            'retail': {'sales', 'retail', 'merchandising', 'customer service', 'shop', 'store', 'commerce', 'trading'}
        }
        
        # Hindi occupation terms
        self.hindi_terms = {
            'कर्मचारी', 'मजदूर', 'कारीगर', 'तकनीशियन', 'सहायक', 'प्रबंधक',
            'अधिकारी', 'इंजीनियर', 'चालक', 'संचालक', 'निरीक्षक', 'पर्यवेक्षक',
            'विशेषज्ञ', 'सलाहकार', 'शिक्षक', 'डॉक्टर', 'नर्स', 'लिपिक'
        }
        
        # Task action verbs
        self.action_verbs = {
            'manages', 'supervises', 'coordinates', 'directs', 'oversees', 'leads',
            'operates', 'controls', 'handles', 'maintains', 'repairs', 'services',
            'performs', 'conducts', 'executes', 'carries out', 'implements', 'processes',
            'analyzes', 'evaluates', 'assesses', 'monitors', 'inspects', 'checks',
            'designs', 'develops', 'creates', 'builds', 'constructs', 'assembles',
            'teaches', 'trains', 'instructs', 'guides', 'mentors', 'educates',
            'sells', 'markets', 'promotes', 'negotiates', 'communicates', 'liaises',
            'prepares', 'organizes', 'plans', 'schedules', 'documents', 'records'
        }
        
    def _compile_patterns(self):
        """Compile regex patterns for extraction"""
        # NCO code variations
        self.nco_pattern = re.compile(r'(\d{4})[.,](\d{3,4})')
        
        # Hindi text detection
        self.hindi_pattern = re.compile(r'[\u0900-\u097F]+')
        
        # Synonym extraction patterns
        self.synonym_patterns = [
            re.compile(r'(?:also\s+(?:known|called|referred\s+to)\s+as)[:\s]+([^.;]+)', re.IGNORECASE),
            re.compile(r'(?:synonyms?|alternate\s+names?)[:\s]+([^.;]+)', re.IGNORECASE),
            re.compile(r'KATEX_INLINE_OPEN([^)]{3,50})KATEX_INLINE_CLOSE'),  # Parenthetical content
            re.compile(r'(?:or|aka|a\.k\.a\.?)\s+([^,;.]+)(?=[,;.]|$)', re.IGNORECASE),
            re.compile(r'/\s*([^/,;.]{3,30})\s*(?=[/,;.]|$)'),  # Slash alternatives
        ]
        
        # Task extraction patterns
        self.task_patterns = []
        for verb in self.action_verbs:
            pattern = re.compile(rf'\b{verb}s?\s+(.+?)(?:[.;]|\s+and\s+|\s*,\s*(?:{"|".join(self.action_verbs)}))', re.IGNORECASE)
            self.task_patterns.append(pattern)
            
    def extract_hierarchy(self, nco_code: str) -> OccupationHierarchy:
        """Extract detailed hierarchy with validation"""
        # Normalize code format
        match = self.nco_pattern.match(nco_code.replace(' ', ''))
        if not match:
            logger.warning(f"Invalid NCO code format: {nco_code}")
            return self._default_hierarchy()
            
        major_part = match.group(1)
        unit_part = match.group(2)
        
        # Extract hierarchy levels
        division = major_part[0] if len(major_part) >= 1 else '?'
        sub_division = major_part[1] if len(major_part) >= 2 else '0'
        minor_group = major_part[2] if len(major_part) >= 3 else '0'
        unit_group = major_part[3] if len(major_part) >= 4 else '0'
        
        # Get division info
        div_info = self.division_mapping.get(division, {'name': f'Division {division}', 'skill_level': 'Unknown'})
        
        # Determine skill specialization
        skill_spec = self._determine_skill_specialization(division, sub_division)
        
        return OccupationHierarchy(
            division=division,
            division_name=div_info['name'],
            sub_division=f"{division}{sub_division}",
            major_group=major_part[:2],
            sub_major_group=major_part[:3],
            minor_group=major_part,
            unit_group=f"{major_part}.{unit_part}",
            skill_level=div_info['skill_level'],
            skill_specialization=skill_spec
        )
        
    def _determine_skill_specialization(self, division: str, sub_division: str) -> str:
        """Determine skill specialization based on codes"""
        specializations = {
            '11': 'Chief Executives and Legislators',
            '12': 'Administrative and Commercial Managers',
            '13': 'Production and Specialized Services Managers',
            '14': 'Hospitality, Retail and Other Services Managers',
            '21': 'Science and Engineering Professionals',
            '22': 'Health Professionals',
            '23': 'Teaching Professionals',
            '24': 'Business and Administration Professionals',
            '25': 'Information and Communications Technology Professionals',
            '26': 'Legal, Social and Cultural Professionals',
            '31': 'Science and Engineering Associate Professionals',
            '32': 'Health Associate Professionals',
            '33': 'Business and Administration Associate Professionals',
            '71': 'Building and Related Trades Workers',
            '72': 'Metal, Machinery and Related Trades Workers',
            '73': 'Handicraft and Printing Workers',
            '74': 'Electrical and Electronic Trades Workers',
            '75': 'Food Processing, Wood Working, Garment Workers'
        }
        
        code = f"{division}{sub_division}"
        return specializations.get(code, 'General Occupational Category')
        
    def _default_hierarchy(self) -> OccupationHierarchy:
        """Return default hierarchy for invalid codes"""
        return OccupationHierarchy(
            division='?',
            division_name='Unclassified',
            sub_division='??',
            major_group='??',
            sub_major_group='???',
            minor_group='????',
            unit_group='????.????',
            skill_level='Unknown',
            skill_specialization='Unspecified'
        )
        
    def generate_contextual_synonyms(self, title: str, description: str) -> List[str]:
        """Generate contextual synonyms with high accuracy"""
        synonyms = set()
        title_lower = title.lower()
        desc_lower = description.lower() if description else ""
        full_text = f"{title_lower} {desc_lower}"
        
        # Strategy 1: Extract from patterns
        for pattern in self.synonym_patterns:
            matches = pattern.findall(full_text)
            for match in matches:
                parts = re.split(r'[,;/&]|\s+and\s+', match)
                for part in parts:
                    cleaned = part.strip()
                    if 2 < len(cleaned) < 50 and cleaned != title_lower:
                        synonyms.add(cleaned)
        
        # Strategy 2: Base term variations
        for base in self.occupation_bases:
            if base in title_lower:
                # Extract core term
                core = title_lower.replace(base, '').strip()
                core = re.sub(r'\s+', ' ', core)
                
                if core and len(core) > 2:
                    # Add related variations
                    related_bases = {
                        'worker': ['operator', 'technician', 'specialist'],
                        'operator': ['worker', 'technician', 'handler'],
                        'technician': ['specialist', 'expert', 'professional'],
                        'manager': ['supervisor', 'coordinator', 'head'],
                        'assistant': ['helper', 'aide', 'support staff'],
                        'engineer': ['technician', 'specialist', 'expert']
                    }
                    
                    for related in related_bases.get(base, []):
                        synonyms.add(f"{core} {related}")
        
        # Strategy 3: Industry-specific synonyms
        for industry, terms in self.industry_terms.items():
            if any(term in full_text for term in terms):
                # Add industry-specific variations
                if 'technician' in title_lower:
                    synonyms.add(f"{industry} technician")
                if 'manager' in title_lower:
                    synonyms.add(f"{industry} manager")
                if 'specialist' in title_lower:
                    synonyms.add(f"{industry} specialist")
        
        # Strategy 4: Hindi synonyms
        hindi_matches = self.hindi_pattern.findall(full_text)
        for match in hindi_matches:
            if len(match) > 2:
                synonyms.add(match)
        
        # Strategy 5: Abbreviations and expansions
        abbreviations = {
            'IT': 'Information Technology',
            'HR': 'Human Resources',
            'QC': 'Quality Control',
            'QA': 'Quality Assurance',
            'R&D': 'Research and Development',
            'O&M': 'Operations and Maintenance',
            'P&L': 'Profit and Loss',
            'HSE': 'Health Safety Environment'
        }
        
        for abbr, expansion in abbreviations.items():
            if abbr in title:
                synonyms.add(title.replace(abbr, expansion))
            elif expansion.lower() in title_lower:
                synonyms.add(title_lower.replace(expansion.lower(), abbr))
        
        # Clean and filter
        cleaned_synonyms = []
        for syn in synonyms:
            syn = re.sub(r'\s+', ' ', syn.strip())
            if syn and syn != title and syn != title_lower and len(syn) > 2:
                cleaned_synonyms.append(syn)
        
        # Sort by relevance (longer, more specific first)
        cleaned_synonyms.sort(key=lambda x: (-len(x), x))
        
        return cleaned_synonyms[:15]
        
    def extract_contextual_examples(self, title: str, description: str) -> List[str]:
        """Extract contextual task examples from description"""
        examples = set()
        
        if not description:
            return self._generate_fallback_examples(title)
        
        desc_lower = description.lower()
        
        # Strategy 1: Extract from action patterns
        for pattern in self.task_patterns:
            matches = pattern.findall(description)
            for match in matches:
                task = match.strip()
                # Clean the task
                task = re.sub(r'^(the|a|an)\s+', '', task, flags=re.IGNORECASE)
                task = re.sub(r'\s+', ' ', task)
                task = re.sub(r'[,;]+$', '', task)
                
                if 10 < len(task) < 150:
                    # Make it action-oriented
                    examples.add(task.lower())
        
        # Strategy 2: List extraction
        list_patterns = [
            re.compile(r'(?:^|\n)\s*[-•·▪▫◦‣⁃]\s*([^-•·▪▫◦‣⁃\n]+)', re.MULTILINE),
            re.compile(r'(?:^|\n)\s*\d+[.)]\s*([^\n]+)', re.MULTILINE),
            re.compile(r'(?:^|\n)\s*[a-z][.)]\s*([^\n]+)', re.MULTILINE),
        ]
        
        for pattern in list_patterns:
            matches = pattern.findall(description)
            for match in matches:
                task = match.strip().lower()
                if 10 < len(task) < 150 and any(verb in task for verb in self.action_verbs):
                    examples.add(task)
        
        # Strategy 3: Responsibility extraction
        resp_patterns = [
            r'responsible\s+for\s+([^.;]+)',
            r'duties\s+include\s+([^.;]+)',
            r'involves?\s+([^.;]+)',
            r'includes?\s+([^.;]+)',
            r'such\s+as\s+([^.;]+)'
        ]
        
        for pattern in resp_patterns:
            matches = re.findall(pattern, desc_lower, re.IGNORECASE)
            for match in matches:
                tasks = re.split(r',\s*(?:and\s+)?', match)
                for task in tasks:
                    task = task.strip()
                    if 10 < len(task) < 150:
                        examples.add(task)
        
        # If not enough examples, add context-based ones
        if len(examples) < 3:
            examples.update(self._generate_fallback_examples(title))
        
        # Convert to list and clean
        example_list = []
        for ex in examples:
            # Ensure it starts with a verb
            words = ex.split()
            if words and words[0] not in self.action_verbs:
                # Try to find a verb and restructure
                for i, word in enumerate(words):
                    if word in self.action_verbs or word.endswith('ing'):
                        ex = ' '.join(words[i:])
                        break
            
            ex = re.sub(r'\s+', ' ', ex.strip())
            if ex and len(ex) > 10:
                example_list.append(ex)
        
        # Remove duplicates and sort by length
        example_list = list(dict.fromkeys(example_list))
        example_list.sort(key=lambda x: len(x))
        
        return example_list[:10]
        
    def _generate_fallback_examples(self, title: str) -> Set[str]:
        """Generate fallback examples based on title"""
        examples = set()
        title_lower = title.lower()
        
        # Role-based examples
        if 'manager' in title_lower:
            examples.update([
                "managing team activities and performance",
                "planning and organizing departmental operations",
                "coordinating with other departments and stakeholders",
                "monitoring budget and resource allocation",
                "conducting performance reviews and providing feedback"
            ])
        elif 'engineer' in title_lower:
            examples.update([
                "designing and developing technical solutions",
                "analyzing technical requirements and specifications",
                "troubleshooting and resolving technical issues",
                "maintaining technical documentation",
                "collaborating with cross-functional teams"
            ])
        elif 'technician' in title_lower:
            examples.update([
                "performing technical maintenance and repairs",
                "operating and monitoring equipment",
                "conducting diagnostic tests and inspections",
                "following safety protocols and procedures",
                "maintaining service records and logs"
            ])
        elif 'operator' in title_lower:
            examples.update([
                "operating machinery and equipment safely",
                "monitoring system performance and indicators",
                "performing routine maintenance checks",
                "recording operational data and logs",
                "following standard operating procedures"
            ])
        elif 'clerk' in title_lower or 'assistant' in title_lower:
            examples.update([
                "maintaining records and documentation",
                "providing administrative support",
                "handling correspondence and communications",
                "organizing files and databases",
                "assisting with daily office operations"
            ])
        else:
            # Generic examples
            examples.update([
                f"performing {title_lower} duties and responsibilities",
                "following established procedures and guidelines",
                "maintaining quality standards and compliance",
                "collaborating with team members",
                "ensuring workplace safety and efficiency"
            ])
            
        return examples
        
    def generate_search_keywords(self, title: str, description: str, synonyms: List[str], hierarchy: OccupationHierarchy) -> List[str]:
        """Generate comprehensive search keywords"""
        keywords = set()
        
        # Title keywords
        title_words = re.findall(r'\b[a-zA-Z]{3,}\b', title.lower())
        keywords.update(title_words)
        
        # Important words from description
        if description:
            # Extract nouns and important terms
            desc_words = re.findall(r'\b[a-zA-Z]{4,}\b', description.lower())
            
            # Filter stop words
            stop_words = {
                'this', 'that', 'these', 'those', 'with', 'from', 'they', 
                'been', 'have', 'their', 'which', 'where', 'when', 'what',
                'will', 'would', 'could', 'should', 'about', 'after', 'before'
            }
            
            important_words = [w for w in desc_words if w not in stop_words]
            
            # Prioritize technical terms
            technical_indicators = ['tion', 'ment', 'ing', 'ical', 'ized', 'ator']
            technical_words = [w for w in important_words if any(w.endswith(ind) for ind in technical_indicators)]
            
            keywords.update(technical_words[:10])
            keywords.update(important_words[:20])
        
        # Synonym keywords
        for synonym in synonyms[:10]:
            syn_words = re.findall(r'\b[a-zA-Z]{3,}\b', synonym.lower())
            keywords.update(syn_words)
        
        # Hierarchy keywords
        keywords.add(hierarchy.division_name.lower())
        keywords.add(hierarchy.skill_specialization.lower())
        
        # Industry detection
        full_text = f"{title} {description} {' '.join(synonyms)}".lower()
        for industry, terms in self.industry_terms.items():
            if any(term in full_text for term in terms):
                keywords.add(industry)
                keywords.update(list(terms)[:3])  # Add top industry terms
        
        # Skill level keywords
        if 'Level 4' in hierarchy.skill_level:
            keywords.update(['professional', 'expert', 'specialist', 'senior'])
        elif 'Level 3' in hierarchy.skill_level:
            keywords.update(['technical', 'skilled', 'experienced'])
        elif 'Level 2' in hierarchy.skill_level:
            keywords.update(['skilled', 'trained', 'qualified'])
        elif 'Level 1' in hierarchy.skill_level:
            keywords.update(['entry-level', 'basic', 'elementary'])
        
        # Clean and sort keywords
        cleaned_keywords = []
        for kw in keywords:
            kw = kw.strip().lower()
            if kw and 2 < len(kw) < 30 and kw.isalpha():
                cleaned_keywords.append(kw)
        
        # Remove duplicates and sort by relevance
        cleaned_keywords = list(set(cleaned_keywords))
        cleaned_keywords.sort(key=lambda x: (
            -1 if x in title.lower() else 0,  # Title words first
            -len(x),  # Longer words
            x  # Alphabetical
        ))
        
        return cleaned_keywords[:30]
        
    def enhance_description(self, title: str, original_desc: str, hierarchy: OccupationHierarchy) -> str:
        """Create enhanced description with context"""
        # Start with classification info
        enhanced = f"{title} is classified under NCO-2015 as a {hierarchy.division_name.lower()} occupation"
        
        # Add skill level
        if hierarchy.skill_level != 'Unknown':
            enhanced += f" requiring {hierarchy.skill_level.lower()}"
        
        # Add specialization
        if hierarchy.skill_specialization != 'Unspecified':
            enhanced += f" in the {hierarchy.skill_specialization.lower()} category"
        
        enhanced += "."
        
        # Add original description if substantial
        if original_desc and len(original_desc) > 50:
            # Clean original description
            clean_desc = re.sub(r'\s+', ' ', original_desc.strip())
            clean_desc = clean_desc[0].upper() + clean_desc[1:] if clean_desc else ""
            
            # Ensure it ends with period
            if clean_desc and clean_desc[-1] not in '.!?':
                clean_desc += '.'
                
            enhanced += f" {clean_desc}"
        else:
            # Add contextual description based on division
            context = self._get_division_context(hierarchy.division)
            enhanced += f" {context}"
        
        # Add skill requirements based on level
        skill_context = self._get_skill_context(hierarchy.skill_level)
        if skill_context:
            enhanced += f" {skill_context}"
        
        return enhanced
        
    def _get_division_context(self, division: str) -> str:
        """Get contextual description for division"""
        contexts = {
            '1': "This role involves planning, directing, coordinating and evaluating the overall activities of enterprises, governments and other organizations.",
            '2': "This position requires theoretical and practical application of specialized knowledge gained through extensive education and training.",
            '3': "This occupation involves technical and practical tasks requiring specialized knowledge to support professionals and managers.",
            '4': "This role focuses on organizing, storing, computing and retrieving information, and performing clerical duties.",
            '5': "This position involves providing personal and protective services, selling goods in shops or markets, and related service activities.",
            '6': "This occupation involves producing and harvesting agricultural, forestry and fishery products using traditional and modern techniques.",
            '7': "This role requires applying specific craft and trade skills in construction, metalwork, machinery, printing and related fields.",
            '8': "This position involves operating and monitoring industrial machinery, equipment and assembly lines in manufacturing settings.",
            '9': "This occupation involves performing simple and routine tasks that may require physical effort and limited training.",
            '0': "This role involves military service and defense-related activities requiring specialized training and discipline."
        }
        
        return contexts.get(division, "This occupation involves specialized tasks within its professional domain.")
        
    def _get_skill_context(self, skill_level: str) -> str:
        """Get skill level context"""
        if 'Level 4' in skill_level:
            return "This is a highly skilled position typically requiring university-level education and extensive professional experience."
        elif 'Level 3' in skill_level:
            return "This position requires advanced technical training and significant practical experience in the field."
        elif 'Level 2' in skill_level:
            return "This role requires vocational training or technical education with practical work experience."
        elif 'Level 1' in skill_level:
            return "This position requires basic education and can be learned through on-the-job training."
        return ""
        
    def calculate_quality_score(self, occupation: Dict) -> Dict[str, float]:
        """Calculate multi-dimensional quality score"""
        scores = {
            'completeness': 0.0,
            'accuracy': 0.0,
            'searchability': 0.0,
            'overall': 0.0
        }
        
        # Completeness score (0-10)
        completeness = 0.0
        
        # Title
        if occupation.get('title'):
            completeness += 1.0
            if len(occupation['title']) >= 10:
                completeness += 0.5
            if len(occupation['title'].split()) >= 2:
                completeness += 0.5
        
        # Description
        if occupation.get('description'):
            completeness += 1.0
            desc_len = len(occupation['description'])
            if desc_len >= 100:
                completeness += 1.0
            if desc_len >= 200:
                completeness += 1.0
        
        # Synonyms
        synonyms = occupation.get('synonyms', [])
        if synonyms:
            completeness += 1.0
            if len(synonyms) >= 3:
                completeness += 0.5
            if len(synonyms) >= 5:
                completeness += 0.5
        
        # Examples
        examples = occupation.get('examples', [])
        if examples:
            completeness += 1.0
            if len(examples) >= 3:
                completeness += 0.5
            if len(examples) >= 5:
                completeness += 0.5
        
        # Keywords
        if occupation.get('search_keywords'):
            completeness += 1.0
            if len(occupation['search_keywords']) >= 10:
                completeness += 1.0
        
        scores['completeness'] = min(10.0, completeness)
        
        # Accuracy score (0-10)
        accuracy = 0.0
        
        # Valid NCO code
        if self.nco_pattern.match(occupation.get('nco_code', '')):
            accuracy += 2.0
        
        # Hierarchy accuracy
        hierarchy = occupation.get('hierarchy', {})
        if hierarchy.get('division') in self.division_mapping:
            accuracy += 2.0
        if hierarchy.get('skill_level') != 'Unknown':
            accuracy += 1.0
        
        # Description quality
        desc = occupation.get('description', '')
        if desc and not desc.startswith('This occupation involves specialized tasks'):
            accuracy += 2.0
        
        # Synonym relevance
        title = occupation.get('title', '').lower()
        relevant_synonyms = sum(1 for syn in synonyms if any(word in title for word in syn.split()))
        if relevant_synonyms > 0:
            accuracy += 1.5
        
        # Example quality
        action_examples = sum(1 for ex in examples if any(verb in ex for verb in self.action_verbs))
        if action_examples >= 3:
            accuracy += 1.5
        
        scores['accuracy'] = min(10.0, accuracy)
        
        # Searchability score (0-10)
        searchability = 0.0
        
        # Keyword coverage
        keywords = occupation.get('search_keywords', [])
        if len(keywords) >= 10:
            searchability += 3.0
        elif len(keywords) >= 5:
            searchability += 2.0
        
        # Searchable text length
        searchable = occupation.get('searchable_text', '')
        if len(searchable) >= 200:
            searchability += 2.0
        elif len(searchable) >= 100:
            searchability += 1.0
        
        # Multi-language support
        if any(self.hindi_pattern.search(str(v)) for v in occupation.values() if isinstance(v, str)):
            searchability += 2.0
        
        # Industry coverage
        full_text = f"{title} {desc} {' '.join(synonyms)}".lower()
        industry_matches = sum(1 for terms in self.industry_terms.values() 
                             if any(term in full_text for term in terms))
        if industry_matches >= 2:
            searchability += 2.0
        elif industry_matches >= 1:
            searchability += 1.0
        
        # Unique identifiers
        if occupation.get('nco_code') and hierarchy:
            searchability += 1.0
        
        scores['searchability'] = min(10.0, searchability)
        
        # Overall score (weighted average)
        scores['overall'] = (
            scores['completeness'] * 0.3 +
            scores['accuracy'] * 0.4 +
            scores['searchability'] * 0.3
        )
        
        return scores
        
    def enhance_occupation(self, occupation: Dict) -> Dict:
        """Enhance a single occupation with all features"""
        try:
            # Extract base information
            nco_code = occupation.get('nco_code', '')
            title = occupation.get('title', '')
            original_desc = occupation.get('description', '')
            
            # Skip if no title
            if not title:
                logger.warning(f"Skipping occupation without title: {nco_code}")
                self.stats['skipped_no_title'] += 1
                return None
            
            # Generate hierarchy
            hierarchy = self.extract_hierarchy(nco_code)
            
            # Generate enhanced features
            synonyms = self.generate_contextual_synonyms(title, original_desc)
            description = self.enhance_description(title, original_desc, hierarchy)
            examples = self.extract_contextual_examples(title, original_desc)
            keywords = self.generate_search_keywords(title, description, synonyms, hierarchy)
            
            # Create searchable text
            searchable_parts = [
                title,
                ' '.join(synonyms),
                description,
                ' '.join(examples),
                ' '.join(keywords),
                hierarchy.division_name,
                hierarchy.skill_specialization
            ]
            searchable_text = ' '.join(filter(None, searchable_parts)).lower()
            
            # Build enhanced occupation
            enhanced = {
                'nco_code': nco_code,
                'title': title.strip(),
                'description': description,
                'original_description': original_desc,
                'synonyms': synonyms,
                'examples': examples,
                'hierarchy': hierarchy.to_dict(),
                'search_keywords': keywords,
                'searchable_text': searchable_text,
                'metadata': {
                    'enhancement_version': '2.0',
                    'enhanced_date': '2025-08-08'
                }
            }
            
            # Calculate quality scores
            quality_scores = self.calculate_quality_score(enhanced)
            enhanced['metadata']['quality_scores'] = quality_scores
            enhanced['metadata']['quality_score'] = quality_scores['overall']
            
            self.stats['enhanced'] += 1
            return enhanced
            
        except Exception as e:
            logger.error(f"Error enhancing occupation {nco_code}: {str(e)}")
            self.stats['errors'] += 1
            return None
            
    def process_dataset(self, occupations: List[Dict]) -> List[Dict]:
        """Process entire dataset"""
        enhanced_occupations = []
        
        logger.info(f"Starting enhancement of {len(occupations)} occupations")
        
        for i, occ in enumerate(occupations):
            enhanced = self.enhance_occupation(occ)
            if enhanced:
                enhanced_occupations.append(enhanced)
            
            if (i + 1) % 100 == 0:
                logger.info(f"Processed {i + 1}/{len(occupations)} occupations...")
        
        # Sort by quality score
        enhanced_occupations.sort(key=lambda x: x['metadata']['quality_score'], reverse=True)
        
        return enhanced_occupations
        
    def print_statistics(self, occupations: List[Dict]):
        """Print detailed statistics"""
        print("\n" + "="*70)
        print("ENHANCEMENT STATISTICS")
        print("="*70)
        
        # Basic stats
        print(f"Total occupations processed: {len(occupations)}")
        print(f"Successfully enhanced: {self.stats['enhanced']}")
        print(f"Skipped (no title): {self.stats['skipped_no_title']}")
        print(f"Errors: {self.stats['errors']}")
        
        # Quality distribution
        quality_scores = [occ['metadata']['quality_score'] for occ in occupations]
        if quality_scores:
            avg_quality = sum(quality_scores) / len(quality_scores)
            high_quality = sum(1 for score in quality_scores if score >= 7.0)
            medium_quality = sum(1 for score in quality_scores if 5.0 <= score < 7.0)
            low_quality = sum(1 for score in quality_scores if score < 5.0)
            
            print(f"\nQuality Distribution:")
            print(f"Average quality score: {avg_quality:.2f}/10")
            print(f"High quality (≥7.0): {high_quality} ({high_quality/len(occupations)*100:.1f}%)")
            print(f"Medium quality (5.0-6.9): {medium_quality} ({medium_quality/len(occupations)*100:.1f}%)")
            print(f"Low quality (<5.0): {low_quality} ({low_quality/len(occupations)*100:.1f}%)")
        
        # Feature coverage
        with_synonyms = sum(1 for occ in occupations if occ.get('synonyms'))
        with_examples = sum(1 for occ in occupations if occ.get('examples'))
        with_keywords = sum(1 for occ in occupations if len(occ.get('search_keywords', [])) >= 10)
        
        print(f"\nFeature Coverage:")
        print(f"With synonyms: {with_synonyms} ({with_synonyms/len(occupations)*100:.1f}%)")
        print(f"With examples: {with_examples} ({with_examples/len(occupations)*100:.1f}%)")
        print(f"With 10+ keywords: {with_keywords} ({with_keywords/len(occupations)*100:.1f}%)")
        
        # Division breakdown
        division_counts = defaultdict(int)
        for occ in occupations:
            division = occ['hierarchy']['division']
            division_counts[division] += 1
        
        print(f"\nDivision Distribution:")
        for div in sorted(division_counts.keys()):
            if div in self.division_mapping:
                name = self.division_mapping[div]['name']
                count = division_counts[div]
                print(f"  {div} - {name}: {count} ({count/len(occupations)*100:.1f}%)")
        
        # Average metrics
        avg_synonyms = sum(len(occ.get('synonyms', [])) for occ in occupations) / len(occupations)
        avg_examples = sum(len(occ.get('examples', [])) for occ in occupations) / len(occupations)
        avg_keywords = sum(len(occ.get('search_keywords', [])) for occ in occupations) / len(occupations)
        
        print(f"\nAverage Metrics:")
        print(f"Synonyms per occupation: {avg_synonyms:.1f}")
        print(f"Examples per occupation: {avg_examples:.1f}")
        print(f"Keywords per occupation: {avg_keywords:.1f}")
        
        print("="*70)

def main():
    """Main processing function"""
    # Setup paths
    script_dir = Path(__file__).parent
    input_path = script_dir.parent / 'nco_data.json'
    output_path = script_dir.parent / 'nco_data_enhanced.json'
    sample_path = script_dir.parent / 'nco_data_enhanced.sample.json'
    
    # Check input file
    if not input_path.exists():
        logger.error(f"Input file not found: {input_path}")
        return
    
    # Load data
    logger.info(f"Loading data from {input_path}")
    with open(input_path, 'r', encoding='utf-8') as f:
        occupations = json.load(f)
    
    logger.info(f"Loaded {len(occupations)} occupations")
    
    # Process data
    enhancer = NCOEnhancer()
    enhanced_occupations = enhancer.process_dataset(occupations)
    
    # Save enhanced data
    logger.info(f"Saving enhanced data to {output_path}")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(enhanced_occupations, f, indent=2, ensure_ascii=False)
    
    # Create sample
    sample_size = min(100, len(enhanced_occupations))
    sample_data = enhanced_occupations[:sample_size]
    with open(sample_path, 'w', encoding='utf-8') as f:
        json.dump(sample_data, f, indent=2, ensure_ascii=False)
    
    # Print statistics
    enhancer.print_statistics(enhanced_occupations)
    
    # Show top examples
    print("\n" + "="*70)
    print("TOP QUALITY OCCUPATIONS (SAMPLES)")
    print("="*70)
    
    for i, occ in enumerate(enhanced_occupations[:5]):
        print(f"\n{i+1}. [{occ['nco_code']}] {occ['title']}")
        print(f"   Division: {occ['hierarchy']['division_name']}")
        print(f"   Skill Level: {occ['hierarchy']['skill_level']}")
        print(f"   Quality Score: {occ['metadata']['quality_score']:.2f}/10")
        print(f"   Synonyms ({len(occ['synonyms'])}): {', '.join(occ['synonyms'][:3])}...")
        print(f"   Examples ({len(occ['examples'])}): {occ['examples'][0] if occ['examples'] else 'None'}")
        print(f"   Keywords ({len(occ['search_keywords'])}): {', '.join(occ['search_keywords'][:5])}...")
    
    print(f"\n✅ Enhancement complete!")
    print(f"📁 Enhanced data saved to: {output_path}")
    print(f"📁 Sample data saved to: {sample_path}")
    print(f"\nTotal enhanced occupations: {len(enhanced_occupations)}")

if __name__ == "__main__":
    main()