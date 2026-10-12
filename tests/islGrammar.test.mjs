import assert from 'node:assert/strict';
import test from 'node:test';
import { translateEnglishToISLGloss, lemmatizeWord } from '../src/lib/islGrammar.ts';

test('ISL Grammar Engine - Lemmatization', () => {
  assert.equal(lemmatizeWord('going'), 'GO');
  assert.equal(lemmatizeWord('went'), 'GO');
  assert.equal(lemmatizeWord('students'), 'STUDENT');
  assert.equal(lemmatizeWord('books'), 'BOOK');
  assert.equal(lemmatizeWord('crying'), 'CRY');
  assert.equal(lemmatizeWord('eating'), 'EAT');
  assert.equal(lemmatizeWord('drank'), 'DRINK');
});

const testCases = [
  // 1. Basic SOV
  { input: 'I drink water', expected: 'I WATER DRINK' },
  // 2. Time fronting with SOV
  { input: 'I am going to school tomorrow', expected: 'TOMORROW I SCHOOL GO' },
  // 3. Verb lemmatization & article removal
  { input: 'She is eating an apple', expected: 'SHE APPLE EAT' },
  // 4. Plural noun lemmatization & copula removal
  { input: 'The students read books', expected: 'STUDENT BOOK READ' },
  // 5. Negation placed after verb
  { input: 'I do not eat meat', expected: 'I MEAT EAT NOT' },
  // 6. Time + Subject + Object + Verb + Negation
  { input: 'Tomorrow he will not play football', expected: 'TOMORROW HE FOOTBALL PLAY NOT' },
  // 7. WH-Question: WHERE at end
  { input: 'Where are you going?', expected: 'YOU GO WHERE' },
  // 8. WH-Question: WHAT at end
  { input: 'What is your name?', expected: 'YOUR NAME WHAT' },
  // 9. WH-Question: WHY at end
  { input: 'Why are you crying?', expected: 'YOU CRY WHY' },
  // 10. WH-Question: WHO at end
  { input: 'Who is teaching English?', expected: 'ENGLISH TEACH WHO' },
  // 11. WH-Question: HOW at end
  { input: 'How are you travelling?', expected: 'YOU TRAVEL HOW' },
  // 12. Past tense lemmatization + Time marker
  { input: 'Yesterday we visited the doctor', expected: 'YESTERDAY WE DOCTOR VISIT' },
  // 13. Stop words (articles, prepositions) removal
  { input: 'The boy looked at the picture', expected: 'BOY PICTURE LOOK' },
  // 14. Time + WH-Question
  { input: 'Where are you going tomorrow?', expected: 'TOMORROW YOU GO WHERE' },
  // 15. Past negation + Time marker
  { input: 'She did not come yesterday', expected: 'YESTERDAY SHE COME NOT' },
  // 16. Greeting at opening
  { input: 'Hello my friend', expected: 'HELLO MY FRIEND' },
  // 17. Multi-clause sequence
  { input: 'Hello. I want water.', expected: 'HELLO I WATER WANT' },
  // 18. Daily time marker + SOV
  { input: 'Today teacher helps students', expected: 'TODAY TEACHER STUDENT HELP' },
  // 19. Modal negation (cannot)
  { input: 'I cannot understand this', expected: 'I THIS UNDERSTAND NOT' },
  // 20. Night/tonight time marker
  { input: 'Tonight we watch movie', expected: 'TONIGHT WE MOVIE WATCH' },
  // 21. WH-Question: WHEN at end
  { input: 'When will you come?', expected: 'YOU COME WHEN' },
  // 22. Transitive verb and direct object
  { input: 'He writes a letter', expected: 'HE LETTER WRITE' },
  // 23. Auxiliary verb & participle removal
  { input: 'They were running in the morning', expected: 'MORNING THEY RUN' },
  // 24. WH-Question: WHICH at end
  { input: 'Which book do you want?', expected: 'YOU BOOK WANT WHICH' },
  // 25. Yesterday negation with plural noun
  { input: 'Yesterday I did not buy books', expected: 'YESTERDAY I BOOK BUY NOT' },
  // 26. Greeting + Question
  { input: 'Namaste, how are you?', expected: 'NAMASTE YOU HOW' },
  // 27. Emergency triage sentence
  { input: 'Doctor needs help', expected: 'DOCTOR HELP NEED' },
  // 28. Sentence with adjective modifier
  { input: 'Doctor needs immediate help', expected: 'DOCTOR HELP IMMEDIATE NEED' }
];

test('27 Real ISL Grammar Sentence -> Gloss Test Cases', () => {
  let passedCount = 0;
  for (const { input, expected } of testCases) {
    const result = translateEnglishToISLGloss(input);
    const actual = result.islGloss;
    console.log(`[TEST] "${input}"\n       Actual:   "${actual}"\n       Expected: "${expected}"`);
    assert.equal(actual, expected, `Mismatch for input: "${input}"`);
    passedCount++;
  }
  console.log(`\nAll ${passedCount} / ${testCases.length} ISL Grammar unit tests passed successfully!`);
});
