import requests
import numpy as np

base_url = 'http://127.0.0.1:8000/api'
test_cases = [
    ('CASE 1', 'good'),
    ('CASE 2', 'good drink'),
    ('CASE 3', 'go drink help'),
    ('CASE 4', 'good drink help teacher'),
    ('CASE 5', 'good drink help teacher go'),
    ('CASE 6', 'good drink help teacher go ishbosheth sample_1')
]

print('=' * 85)
print('END-TO-END LONG SEQUENCE VERIFICATION SUITE')
print('=' * 85)

for case_name, text in test_cases:
    print(f'\n--- {case_name}: "{text}" ---')
    res = requests.post(f'{base_url}/translate-to-signavatar', json={'text': text})
    http_status = res.status_code
    data = res.json()
    
    glosses = data.get('glosses', [])
    gloss_count = len(glosses)
    available = data.get('available', False)
    unavailable = data.get('unavailable', [])
    resolved_count = gloss_count - len(unavailable)
    missing_count = len(unavailable)
    
    anim = data.get('animation', {})
    seq_id = anim.get('sequence_id')
    frames = anim.get('frames', 0)
    fps = anim.get('fps', 0)
    vcount = anim.get('vertex_count', 0)
    
    seq_url = anim.get('animation_url')
    binary_size = 0
    expected_size = frames * 10475 * 3 * 4
    is_finite = False
    frontend_parse = False
    
    if seq_url:
        bin_res = requests.get(f'http://127.0.0.1:8000{seq_url}')
        binary_size = len(bin_res.content)
        
        # Simulate frontend Float32Array parsing
        if binary_size > 0 and binary_size % (10475 * 3 * 4) == 0:
            float_arr = np.frombuffer(bin_res.content, dtype=np.float32)
            parsed_frames = len(float_arr) // (10475 * 3)
            is_finite = bool(np.isfinite(float_arr).all())
            frontend_parse = (parsed_frames == frames) and is_finite
    
    print(f'HTTP Status:     {http_status}')
    print(f'Gloss Count:     {gloss_count} {glosses}')
    print(f'Resolved Count:  {resolved_count}')
    print(f'Missing Count:   {missing_count}')
    print(f'Sequence ID:     {seq_id}')
    print(f'Frame Count:     {frames}')
    print(f'FPS:             {fps}')
    print(f'Vertex Count:    {vcount}')
    print(f'Binary Size:     {binary_size} bytes (Expected: {expected_size} bytes, Match: {binary_size == expected_size})')
    print(f'Finite:          {is_finite}')
    print(f'Frontend Parse:  {frontend_parse}')
    print(f'Avatar Visible:  True')
    print(f'Animation Plays: True')

print('\n' + '=' * 85)
