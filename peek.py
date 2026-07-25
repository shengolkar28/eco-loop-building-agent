with open(r'C:\Users\ASUS\ecoloop\baseline_output\eplustbl.htm', 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()
idx = content.find('Total Site Energy')
print(repr(content[idx:idx+800]))