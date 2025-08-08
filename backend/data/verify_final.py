#!/usr/bin/env python3
import json

def main():
    with open('../nco_data.json', encoding='utf-8') as f:
        data = json.load(f)
    
    print('📊 FINAL DATASET STATISTICS')
    print('='*50)
    print(f'Total occupations: {len(data):,}')
    print(f'Target (3,600): 3,600')
    print(f'Achievement: {len(data)/3600*100:.1f}%')
    
    occ = data[0]
    print('\n📝 DATA STRUCTURE:')
    for key in occ.keys():
        print(f'  ✓ {key}')
    
    print('\n🔍 SAMPLE OCCUPATION:')
    print(f'Code: {occ["nco_code"]}')
    print(f'Title: {occ["title"]}')
    print(f'Division: {occ["hierarchy"]["division_name"]}')
    print(f'Quality: {occ["metadata"]["quality_score"]}/10')
    print(f'Synonyms: {", ".join(occ["synonyms"][:3]) if occ["synonyms"] else "None"}')
    print(f'Examples: {occ["examples"][0] if occ["examples"] else "None"}')
    print(f'Keywords: {", ".join(occ["search_keywords"][:5]) if occ["search_keywords"] else "None"}')

if __name__ == "__main__":
    main()
