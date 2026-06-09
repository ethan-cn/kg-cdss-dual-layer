fp = r'D:\Cursor\development_cdsis\paper1_dev\git_upload\kg-cdss-dual-layer\docs\Paper1_Manuscript.md'
with open(fp, 'r', encoding='utf-8') as f:
    lines = f.readlines()
for i, l in enumerate(lines[707:714], start=708):
    print(f"{i}: {repr(l)}")
