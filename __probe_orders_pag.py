import sys
target_path = r'C:\Users\actpie\Desktop\Github -线下\Supply-Chain-Management\templates\orders\list.html'
with open(target_path, 'rb') as f:
    data = f.read()
content = data.decode('utf-8')
# Find the pagination block boundaries via structure
i = content.find('{% if pagination and pagination.pages > 1 %}')
print('pag_start:', i)
# Show full pagination block
e = i
depth = 0
while True:
    a = content.find('{% if ', e)
    b = content.find('{% endif %}', e)
    if a != -1 and a < b:
        depth += 1
        e = a + 1
    elif b != -1:
        depth -= 1
        e = b + len('{% endif %}')
        if depth < 0:
            break
print('pag_end:', e)
sys.stdout.buffer.write(content[i-30:e+30].encode('utf-8'))