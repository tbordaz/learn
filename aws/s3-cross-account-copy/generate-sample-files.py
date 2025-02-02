import os

# Create a directory for the sample files
os.makedirs('sample_files', exist_ok=True)

# Create 10 text files with 10 bytes each
for i in range(10):
    with open(f'sample_files/file_{i+1}.txt', 'w') as f:
        f.write('1234567890')  # 10 bytes of content
