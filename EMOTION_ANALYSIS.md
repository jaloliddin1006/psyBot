# Emotion Analysis Feature

## Overview

The Emotion Analysis feature provides users with comprehensive insights into their emotional patterns based on their emotion diary entries. It offers both short-term text analysis and detailed PDF reports for longer periods.

## How to Access

1. From the main menu, tap "Аналитика эмоций" (Emotion Analysis)
2. Select the time period you want to analyze:
   - 3 дня (3 days) - Text analysis
   - Неделя (7 days) - PDF report
   - Две недели (14 days) - PDF report
   - Месяц (30 days) - PDF report
   - 3 месяца (90 days) - PDF report

## Features

### 3-Day Text Analysis

For 3-day periods, the bot provides a detailed text analysis including:

- **Date range** of the analysis
- **Most frequent emotion** experienced during the period
- **Daily breakdown** showing:
  - Day-by-day emotion entries
  - Time stamps for each emotion
  - Emotion details (type and intensity)
  - Context from user's diary entries
- **Positive moments** highlighting joyful experiences
- **AI-generated advice** for the most common negative emotion, considering the contexts in which it occurred

### PDF Reports (7+ days)

For longer periods, the bot generates comprehensive PDF reports containing:

#### Statistics Section
- Total number of emotion entries
- Count of positive vs negative emotions
- Number of days with recorded emotions

#### Top Emotions Analysis
- Top 3 most frequently experienced emotions
- Frequency count for each emotion

#### Positive Moments
- List of recent positive emotional experiences
- Timestamps and emotion details

#### Negative Emotions Analysis
- Top 3 destructive emotions that need attention
- Recommendation to discuss these with a therapist

#### Therapy Topics
- AI-generated suggestions for topics to discuss with a psychologist
- Based on analysis of negative emotion contexts
- Personalized recommendations

#### Praise Section
- Encouragement for maintaining the emotion diary
- Recognition of progress in emotional self-awareness

## Technical Implementation

### Data Sources
- Emotion entries from the `emotion_entries` table
- User information for personalization
- Time-based filtering for selected periods

### Emotion Mapping
The system uses predefined mappings to convert internal emotion codes to human-readable descriptions:

**Positive Emotions:**
- `good_state_1`: Подъем, легкость (Uplift, lightness)
- `good_state_2`: Спокойствие, расслабленность (Calm, relaxation)
- `good_state_3`: Уют, близость (Comfort, closeness)
- `good_state_4`: Интерес, вдохновение (Interest, inspiration)
- `good_state_5`: Сила, уверенность (Strength, confidence)

**Negative Emotions:**
- `bad_state_1`: Тяжесть, усталость (Heaviness, fatigue)
- `bad_state_2`: Тревога, беспокойство (Anxiety, worry)
- `bad_state_3`: Злость, раздражение (Anger, irritation)
- `bad_state_4`: Отстраненность, обида (Detachment, resentment)
- `bad_state_5`: Вина, смущение (Guilt, embarrassment)

### AI Integration
- Uses Google Gemini AI for generating personalized advice
- Analyzes emotion contexts to provide relevant recommendations
- Generates therapy topics based on user's emotional patterns

### PDF Generation
- Uses ReportLab library for professional PDF creation
- Includes tables, formatted text, and structured layout
- Temporary file handling with automatic cleanup

## Error Handling

- Graceful fallback to text reports if PDF generation fails
- Validation of user registration and emotion data availability
- Informative messages when no data is available for selected periods

## Privacy and Data

- All analysis is performed on user's own data only
- No data sharing between users
- Temporary files are automatically deleted after sending
- AI processing uses anonymized emotion contexts

## Future Enhancements

Potential improvements for future versions:
- Graphical charts and visualizations
- Trend analysis over time
- Emotion pattern recognition
- Integration with therapy session scheduling
- Export options for different formats
- Comparative analysis between periods 