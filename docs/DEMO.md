
#### `docs/DEMO.md`
```markdown
# NCO Search Demo Script

This demo script showcases the key features of the NCO Semantic Search system for stakeholders.

## Demo Setup

1. **Pre-demo Checklist**
   - [ ] Backend running and healthy
   - [ ] Frontend loaded in browser
   - [ ] Admin token ready
   - [ ] Clear browser cache
   - [ ] Microphone permissions granted

2. **Browser Setup**
   - Use Chrome for best voice support
   - Open in incognito for clean state
   - Zoom to 110% for visibility

## Demo Flow (10 minutes)

### 1. Introduction (1 min)
"This is the NCO Semantic Search system - an AI-powered tool to help citizens find the right occupation codes in multiple Indian languages."

### 2. Basic Search (2 min)

**English Search**
- Type: "person who fixes cars"
- Show: Results include "Automotive Mechanic"
- Point out: Confidence score, NCO code, matched terms

**Hindi Search**
- Clear search
- Type: "गाड़ी मैकेनिक"
- Show: Same results in Hindi query
- Point out: Language detection badge

### 3. Voice Search (1 min)
- Click microphone icon
- Say in Hindi: "नर्स" (nurse)
- Show: Voice transcription and results
- Point out: Hands-free operation

### 4. Advanced Features (2 min)

**Language Override**
- Search: "tailor"
- Click "HI" language chip
- Show: Results remain accurate
- Explain: Helps when auto-detection uncertain

**Low Confidence Demo**
- Search: "rocket scientist"
- Show: Low confidence banner
- Explain: System knows when unsure

### 5. Result Details (1 min)
- Click on "Tailor" result
- Show: Full occupation details
- Point out: Synonyms in multiple languages
- Show: Examples of work activities

### 6. Feedback System (1 min)
- Return to search
- Click "Helpful?" on a result
- Show: Feedback dialog
- Explain: Continuous improvement

### 7. Admin Features (2 min)

**Login**
- Navigate to `/admin`
- Enter admin token
- Show: Dashboard loads

**Analytics**
- Show: Search statistics
- Point out: Top queries, success rate
- Explain: Data-driven improvements

**Synonym Management**
- Go to Synonyms tab
- Add synonym demo:
  - NCO Code: `7212.0100`
  - Add: "arc welder, TIG welder"
  - Click Update
  - Click Reindex
- Return to search
- Search: "TIG welder"
- Show: Now finds welding occupation

## Demo Queries

### Multilingual Query Set

| Language | Query | Expected Result | NCO Code |
|----------|-------|-----------------|----------|
| English | person who fixes cars | Automotive Mechanic | 7231.0200 |
| English | sews clothes | Tailor | 7533.0101 |
| English | electrical wiring | Electrician General | 7411.0100 |
| English | teaches children | Teacher, Primary School | 2330.0100 |
| Hindi | गाड़ी मैकेनिक | Automotive Mechanic | 7231.0200 |
| Hindi | सिलाई मशीन ऑपरेटर | Tailor | 7533.0101 |
| Hindi | नर्स | Nurse, General | 3221.0101 |
| Hindi | किसान | Farm Worker | 9211.0100 |
| Bengali | গাড়ি মেকানিক | Automotive Mechanic | 7231.0200 |
| Bengali | ডেটা এন্ট্রি | Data Entry Operator | 4131.0100 |
| Bengali | নার্স | Nurse, General | 3221.0101 |
| Bengali | শিক্ষক | Teacher, Primary School | 2330.0100 |
| Marathi | गाडी मेकॅनिक | Automotive Mechanic | 7231.0200 |
| Marathi | शेती काम | Farm Worker | 9211.0100 |
| Marathi | शिक्षक | Teacher, Primary School | 2330.0100 |
| Marathi | वेल्डर | Welder, Gas | 7212.0100 |

### Edge Cases to Demo

1. **Ambiguous Query**: "operator"
   - Shows multiple relevant results
   - Demonstrates ranking

2. **Spelling Variation**: "macanic" (mechanic)
   - Still finds correct result
   - Shows fuzzy matching

3. **Mixed Language**: "computer वाला"
   - Handles code-mixing
   - Common in Indian context

## Key Messages

1. **Accessibility**
   - Multiple languages supported
   - Voice input for low-literacy users
   - Simple, intuitive interface

2. **Accuracy**
   - AI understands context
   - Confidence scoring
   - Continuous improvement

3. **Efficiency**
   - Instant results
   - No training required
   - Works on any device

4. **Transparency**
   - Shows why matched
   - Clear confidence indicators
   - Admin insights

## Common Questions

**Q: How many occupations are included?**
A: Currently 3,600+ occupations from NCO-2015. Full dataset can be loaded.

**Q: Can it work offline?**
A: Not currently, but the model is small enough for edge deployment.

**Q: How accurate is voice recognition?**
A: Depends on browser/device, but generally 90%+ for clear speech.

**Q: Can we add regional languages?**
A: Yes, the model supports 100+ languages. Can add Gujarati, Tamil, etc.

**Q: How do we update occupations?**
A: Through admin panel - add synonyms and reindex in seconds.

## Post-Demo

1. Share demo recording
2. Provide test credentials
3. Collect feedback via form
4. Schedule follow-up for requirements

## Demo Video Script (3 minutes)

**0:00-0:15** - Introduction
"NCO Semantic Search helps citizens find the right occupation codes in seconds, in their own language."

**0:15-0:45** - Search Demo
- English search: "welding"
- Hindi search: "नर्स"
- Voice search demo

**0:45-1:15** - Multilingual Support
- Show Bengali query
- Show Marathi query
- Language selector

**1:15-1:45** - Smart Features
- Low confidence example
- Occupation details
- Feedback system

**1:45-2:30** - Admin Portal
- View analytics
- Update synonyms
- Instant reindex

**2:30-3:00** - Closing
"Ready for deployment across India. Scalable, secure, and citizen-friendly."

## Success Metrics

Track during demo:
- Search success rate: >85%
- Response time: <100ms
- Language detection accuracy: >95%
- Admin operations: <5 seconds