import { VideoProject, ISLDictionaryItem, ChatMessage } from '../types';

export const SAMPLE_PROJECTS: VideoProject[] = [
  {
    id: 'proj-01',
    title: 'AI Accessibility Keynote & Welcome Address',
    originalFileName: 'keynote_accessibility_2026.mp4',
    duration: 34.5,
    createdAt: '12 minutes ago',
    status: 'completed',
    accuracy: 98.4,
    language: 'English (India)',
    dialect: 'standard',
    transcript: 'Hello and welcome everyone. Today we are proud to introduce SignAura, breaking communication barriers for the deaf community across India with artificial intelligence.',
    glossTokens: [
      { id: 'g-1', word: 'Hello', gloss: 'HELLO', startTime: 0.0, endTime: 1.8, confidence: 0.99, grammarTag: 'GREETING' },
      { id: 'g-2', word: 'welcome', gloss: 'WELCOME', startTime: 1.9, endTime: 3.5, confidence: 0.98, grammarTag: 'GREETING' },
      { id: 'g-3', word: 'everyone', gloss: 'ALL-PEOPLE', startTime: 3.6, endTime: 5.2, confidence: 0.97, grammarTag: 'OBJECT' },
      { id: 'g-4', word: 'Today', gloss: 'TODAY', startTime: 5.3, endTime: 7.0, confidence: 0.99, grammarTag: 'TIME_MARKER' },
      { id: 'g-5', word: 'introduce', gloss: 'INTRODUCE', startTime: 7.1, endTime: 9.2, confidence: 0.96, grammarTag: 'VERB' },
      { id: 'g-6', word: 'SignAura', gloss: 'SIGN-AURA-SYSTEM', startTime: 9.3, endTime: 11.5, confidence: 0.98, grammarTag: 'NOUN' },
      { id: 'g-7', word: 'barrier', gloss: 'BARRIER-REMOVE', startTime: 11.6, endTime: 14.0, confidence: 0.95, grammarTag: 'VERB' },
      { id: 'g-8', word: 'deaf', gloss: 'DEAF-COMMUNITY', startTime: 14.1, endTime: 16.8, confidence: 0.99, grammarTag: 'SUBJECT' },
      { id: 'g-9', word: 'India', gloss: 'INDIA', startTime: 16.9, endTime: 19.5, confidence: 0.99, grammarTag: 'LOCATION' },
      { id: 'g-10', word: 'accessible', gloss: 'ACCESSIBLE-FUTURE', startTime: 19.6, endTime: 22.5, confidence: 0.97, grammarTag: 'OBJECT' }
    ]
  },
  {
    id: 'proj-02',
    title: 'Emergency Medical First Responder Instructions',
    originalFileName: 'hospital_triage_guideline.mp4',
    duration: 48.0,
    createdAt: '2 hours ago',
    status: 'completed',
    accuracy: 99.1,
    language: 'English / Hindi',
    dialect: 'north',
    transcript: 'Doctor is coming immediately. Please stay calm and tell me where it hurts.',
    glossTokens: [
      { id: 'g-201', word: 'Doctor', gloss: 'DOCTOR', startTime: 0.0, endTime: 2.2, confidence: 0.99, grammarTag: 'SUBJECT' },
      { id: 'g-202', word: 'coming', gloss: 'COME-QUICK', startTime: 2.3, endTime: 4.5, confidence: 0.98, grammarTag: 'VERB' },
      { id: 'g-203', word: 'Please', gloss: 'PLEASE-CALM', startTime: 4.6, endTime: 7.0, confidence: 0.99, grammarTag: 'MODIFIER' },
      { id: 'g-204', word: 'pain', gloss: 'PAIN-WHERE', startTime: 7.1, endTime: 9.8, confidence: 0.97, grammarTag: 'QUESTION_MARKER' }
    ]
  },
  {
    id: 'proj-03',
    title: 'Classroom Lecture: Computer Science Fundamentals',
    originalFileName: 'cs101_algorithms_intro.mp4',
    duration: 120.0,
    createdAt: '1 day ago',
    status: 'completed',
    accuracy: 96.5,
    language: 'English',
    dialect: 'south',
    transcript: 'In this lesson we will understand how data structures and algorithms solve complex problems step by step.',
    glossTokens: [
      { id: 'g-301', word: 'Lesson', gloss: 'LEARN-CLASS', startTime: 0.0, endTime: 2.5, confidence: 0.96, grammarTag: 'TOPIC' },
      { id: 'g-302', word: 'Computer', gloss: 'COMPUTER-ALGORITHM', startTime: 2.6, endTime: 5.2, confidence: 0.97, grammarTag: 'OBJECT' },
      { id: 'g-303', word: 'Solve', gloss: 'PROBLEM-SOLVE', startTime: 5.3, endTime: 8.0, confidence: 0.95, grammarTag: 'VERB' }
    ]
  },
  {
    id: 'proj-04',
    title: 'Daily Metro Transit Announcement',
    originalFileName: 'delhi_metro_yellow_line.mp4',
    duration: 18.0,
    createdAt: '3 days ago',
    status: 'completed',
    accuracy: 99.4,
    language: 'Hindi / English',
    dialect: 'standard',
    transcript: 'Next station is Rajiv Chowk. Doors will open on the left.',
    glossTokens: [
      { id: 'g-401', word: 'Station', gloss: 'TRAIN-STATION-NEXT', startTime: 0.0, endTime: 2.4, confidence: 0.99, grammarTag: 'LOCATION' },
      { id: 'g-402', word: 'Door', gloss: 'DOOR-OPEN-LEFT', startTime: 2.5, endTime: 5.0, confidence: 0.98, grammarTag: 'VERB' }
    ]
  }
];

export const ISL_DICTIONARY: ISLDictionaryItem[] = [
  {
    id: 'dict-1',
    word: 'Hello',
    gloss: 'HELLO',
    category: 'Greetings',
    definition: 'Open flat right hand raised near temple moving gently forward in welcoming gesture.',
    exampleSentence: 'Hello, welcome to SignAura.',
    difficulty: 'Beginner'
  },
  {
    id: 'dict-2',
    word: 'Welcome',
    gloss: 'WELCOME',
    category: 'Greetings',
    definition: 'Both hands open with palms facing upward sweeping gently inward toward chest.',
    exampleSentence: 'We welcome you to our community.',
    difficulty: 'Beginner'
  },
  {
    id: 'dict-3',
    word: 'Thank You',
    gloss: 'THANK_YOU',
    category: 'Greetings',
    definition: 'Flat hand fingertips touching chin/lips then moving outward towards recipient.',
    exampleSentence: 'Thank you for your assistance.',
    difficulty: 'Beginner'
  },
  {
    id: 'dict-4',
    word: 'How Are You',
    gloss: 'HOW_ARE_YOU',
    category: 'Conversational',
    definition: 'Curved hands rotating outwards followed by pointing gesture with raised eyebrows (question marker).',
    exampleSentence: 'Hello friend, how are you today?',
    difficulty: 'Intermediate'
  },
  {
    id: 'dict-5',
    word: 'Sign Language',
    gloss: 'SIGN_LANGUAGE',
    category: 'Education',
    definition: 'Alternating circular rolling motion of both open hands in front of chest.',
    exampleSentence: 'Indian Sign Language is rich and expressive.',
    difficulty: 'Intermediate'
  },
  {
    id: 'dict-6',
    word: 'Accessible',
    gloss: 'ACCESSIBLE',
    category: 'Technology',
    definition: 'Interlocking curved fingers smoothly opening outward representing barrier removal.',
    exampleSentence: 'Our mission is to make all digital media accessible.',
    difficulty: 'Intermediate'
  },
  {
    id: 'dict-7',
    word: 'India',
    gloss: 'INDIA',
    category: 'Conversational',
    definition: 'Thumb of right fist touching forehead (representing bindi/tilak) with respectful tilt.',
    exampleSentence: 'Indian Sign Language unites millions across India.',
    difficulty: 'Beginner'
  },
  {
    id: 'dict-8',
    word: 'Deaf Community',
    gloss: 'DEAF',
    category: 'Conversational',
    definition: 'Index finger touching ear then moving to touch corner of mouth, followed by open palm group arc.',
    exampleSentence: 'Empowering the deaf community through spatial AI.',
    difficulty: 'Beginner'
  },
  {
    id: 'dict-9',
    word: 'Help',
    gloss: 'HELP',
    category: 'Emergency',
    definition: 'Right closed fist resting on flat left palm, both hands lifting upward together.',
    exampleSentence: 'Do you need help with translation?',
    difficulty: 'Beginner'
  },
  {
    id: 'dict-10',
    word: 'Doctor / Medical',
    gloss: 'DOCTOR',
    category: 'Medical',
    definition: 'Fingertips of right hand tapping the inside wrist pulse point of the left arm.',
    exampleSentence: 'The doctor is ready for your consultation.',
    difficulty: 'Intermediate'
  }
];

export const INITIAL_CHAT_MESSAGES: ChatMessage[] = [
  {
    id: 'msg-1',
    sender: 'ai',
    text: 'Hello! I am your SignAura AI Assistant. You can ask me to translate sentences into Indian Sign Language (ISL) grammar, explain non-manual markers, or generate 3D avatar animations in real-time. How can I assist you?',
    timestamp: 'Just now',
    glossSequence: ['HELLO', 'WELCOME', 'SIGN-AURA-AI', 'HELP-YOU-CAN'],
    recommendedSigns: ['HELLO', 'WELCOME', 'HOW_ARE_YOU', 'ACCESSIBLE']
  }
];
