#!/usr/bin/env python3
"""
nco_hierarchy.py

Enhances NCO data with hierarchical structure (Division -> Sub-Division -> Group -> Family).
Adds support for 8-digit code parsing and hierarchy extraction.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def parse_nco_code(code: str) -> Dict[str, str]:
    """
    Parse NCO code into hierarchical components.
    NCO-2015 uses 4-digit.4-digit format where:
    - First digit: Division (Major Group)
    - First 2 digits: Sub-Division
    - First 3 digits: Minor Group
    - First 4 digits: Unit Group
    - Full 8 digits: Specific Occupation
    
    Example: 7212.0100
    - Division: 7 (Craft and Related Trade Workers)
    - Sub-Division: 72 (Metal, Machinery and Related Trade Workers)
    - Minor Group: 721 (Metal Moulders, Welders, Sheet Metal Workers, Structural Metal Preparers and Related Trades Workers)
    - Unit Group: 7212 (Welders and Flame Cutters)
    - Occupation: 7212.0100 (Welder, Gas)
    """
    if not re.match(r'^\d{4}\.\d{4}$', code):
        return {}
    
    parts = code.split('.')
    main_part = parts[0]
    
    return {
        'division': main_part[0],
        'sub_division': main_part[:2],
        'minor_group': main_part[:3],
        'unit_group': main_part[:4],
        'occupation_code': code
    }


def load_hierarchy_mappings() -> Dict[str, Dict[str, str]]:
    """
    Load or define NCO-2015 hierarchy mappings.
    Returns division/sub-division names based on NCO-2015 structure.
    """
    # NCO-2015 Division structure
    divisions = {
        '1': 'Legislators, Senior Officials and Managers',
        '2': 'Professionals',
        '3': 'Technicians and Associate Professionals',
        '4': 'Clerks',
        '5': 'Service Workers and Shop and Market Sales Workers',
        '6': 'Skilled Agricultural and Fishery Workers',
        '7': 'Craft and Related Trade Workers',
        '8': 'Plant and Machine Operators and Assemblers',
        '9': 'Elementary Occupations',
        '0': 'Armed Forces'
    }
    
    # Sample sub-divisions (can be expanded from Vol-I mapping)
    sub_divisions = {
        '11': 'Legislators and Senior Officials',
        '12': 'Corporate Managers',
        '13': 'Managers of Small Enterprises',
        '21': 'Physical, Mathematical and Engineering Science Professionals',
        '22': 'Life Science and Health Professionals',
        '23': 'Teaching Professionals',
        '24': 'Other Professionals',
        '31': 'Physical and Engineering Science Associate Professionals',
        '32': 'Life Science and Health Associate Professionals',
        '33': 'Teaching Associate Professionals',
        '34': 'Other Associate Professionals',
        '41': 'Office Clerks',
        '42': 'Customer Service Clerks',
        '51': 'Personal and Protective Service Workers',
        '52': 'Models, Salespersons and Demonstrators',
        '61': 'Skilled Agricultural and Fishery Workers',
        '71': 'Extraction and Building Trade Workers',
        '72': 'Metal, Machinery and Related Trade Workers',
        '73': 'Precision, Handicraft, Craft Printing and Related Trade Workers',
        '74': 'Other Craft and Related Trade Workers',
        '81': 'Stationary Plant and Related Operators',
        '82': 'Machine Operators and Assemblers',
        '83': 'Drivers and Mobile Plant Operators',
        '91': 'Sales and Services Elementary Occupations',
        '92': 'Agricultural, Fishery and Related Labourers',
        '93': 'Labourers in Mining, Construction, Manufacturing and Transport'
    }
    
    return {
        'divisions': divisions,
        'sub_divisions': sub_divisions
    }


def enhance_occupation_with_hierarchy(occupation: Dict, hierarchy_mappings: Dict) -> Dict:
    """
    Enhance occupation record with hierarchical information.
    """
    code = occupation.get('nco_code', '')
    hierarchy = parse_nco_code(code)
    
    if hierarchy:
        # Add hierarchy fields
        occupation['hierarchy'] = {
            'division_code': hierarchy['division'],
            'division_name': hierarchy_mappings['divisions'].get(hierarchy['division'], 'Unknown'),
            'sub_division_code': hierarchy['sub_division'],
            'sub_division_name': hierarchy_mappings['sub_divisions'].get(hierarchy['sub_division'], 'Unknown'),
            'minor_group_code': hierarchy['minor_group'],
            'unit_group_code': hierarchy['unit_group'],
            'full_code': code
        }
        
        # Generate hierarchical breadcrumb for UI
        occupation['breadcrumb'] = [
            hierarchy_mappings['divisions'].get(hierarchy['division'], 'Unknown'),
            hierarchy_mappings['sub_divisions'].get(hierarchy['sub_division'], 'Unknown'),
            occupation['title']
        ]
    
    return occupation


def extract_synonyms_from_description(description: str) -> List[str]:
    """
    Extract potential synonyms and alternate names from occupation description.
    Uses pattern matching to find common synonym patterns like:
    - "also known as..."
    - "may be designated as..."
    - "includes..."
    """
    synonyms = []
    
    # Pattern for "also known as", "also called", etc.
    aka_pattern = r'(?:also known as|also called|may be designated as|includes?)\s*[:;]?\s*([^.;]+)'
    matches = re.findall(aka_pattern, description, re.IGNORECASE)
    
    for match in matches:
        # Split by common delimiters
        terms = re.split(r'[,;]|\band\b|\bor\b', match)
        for term in terms:
            cleaned = term.strip().strip('"\'')
            if cleaned and len(cleaned) > 2:
                synonyms.append(cleaned)
    
    return list(set(synonyms))  # Remove duplicates


def generate_occupation_examples(occupation: Dict) -> List[str]:
    """
    Generate example job titles or variations based on the occupation.
    """
    examples = []
    title = occupation.get('title', '')
    
    # Extract base role from title
    if ',' in title:
        parts = title.split(',')
        base_role = parts[0].strip()
        qualifier = parts[1].strip() if len(parts) > 1 else ''
        
        # Generate variations
        if qualifier:
            examples.append(f"{qualifier} {base_role}")
            examples.append(f"{base_role} ({qualifier})")
    
    # Add common prefixes/suffixes
    common_prefixes = ['Senior', 'Junior', 'Assistant', 'Chief', 'Lead']
    common_suffixes = ['Specialist', 'Expert', 'Technician', 'Officer']
    
    base_title = title.split(',')[0].strip()
    
    # Only add a few variations to avoid noise
    for prefix in common_prefixes[:2]:
        if prefix.lower() not in base_title.lower():
            examples.append(f"{prefix} {base_title}")
            break
    
    return examples[:5]  # Limit to 5 examples


def enhance_nco_data(input_json: Path, output_json: Path) -> None:
    """
    Enhance NCO data with hierarchy, extracted synonyms, and examples.
    """
    print(f"Loading NCO data from {input_json}")
    with open(input_json, 'r', encoding='utf-8') as f:
        occupations = json.load(f)
    
    print(f"Loaded {len(occupations)} occupations")
    
    # Load hierarchy mappings
    hierarchy_mappings = load_hierarchy_mappings()
    
    # Enhance each occupation
    enhanced_occupations = []
    for occ in occupations:
        # Add hierarchy
        occ = enhance_occupation_with_hierarchy(occ, hierarchy_mappings)
        
        # Extract synonyms from description if not already present
        if not occ.get('synonyms'):
            occ['synonyms'] = extract_synonyms_from_description(occ.get('description', ''))
        
        # Generate examples if not present
        if not occ.get('examples'):
            occ['examples'] = generate_occupation_examples(occ)
        
        # Add metadata
        occ['metadata'] = {
            'version': 'NCO-2015',
            'enhanced': True,
            'source': occ.get('source', 'NCO-2015')
        }
        
        enhanced_occupations.append(occ)
    
    # Sort by NCO code for consistency
    enhanced_occupations.sort(key=lambda x: x['nco_code'])
    
    # Save enhanced data
    print(f"Saving enhanced data to {output_json}")
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(enhanced_occupations, f, ensure_ascii=False, indent=2)
    
    # Print statistics
    total_with_hierarchy = sum(1 for o in enhanced_occupations if 'hierarchy' in o)
    total_with_synonyms = sum(1 for o in enhanced_occupations if o.get('synonyms'))
    total_with_examples = sum(1 for o in enhanced_occupations if o.get('examples'))
    
    print(f"\nEnhancement Statistics:")
    print(f"  - Total occupations: {len(enhanced_occupations)}")
    print(f"  - With hierarchy: {total_with_hierarchy}")
    print(f"  - With synonyms: {total_with_synonyms}")
    print(f"  - With examples: {total_with_examples}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Enhance NCO data with hierarchy and metadata")
    parser.add_argument("--input", default="backend/nco_data.json", help="Input JSON file")
    parser.add_argument("--output", default="backend/nco_data_enhanced.json", help="Output enhanced JSON file")
    
    args = parser.parse_args()
    
    input_path = Path(args.input)
    output_path = Path(args.output)
    
    if not input_path.exists():
        print(f"Error: Input file {input_path} not found")
        exit(1)
    
    enhance_nco_data(input_path, output_path)
