import setuptools

setuptools.setup(
    name='daam',
    version=eval(open('daam/_version.py').read().strip().split('=')[1]),
    author='Raphael Tang',
    license='MIT',
    url='https://github.com/castorini/daam',
    author_email='r33tang@uwaterloo.ca',
    description='What the DAAM: Interpreting Stable Diffusion Using Cross Attention.',
    install_requires=[
      'transformers',
      'diffusers',
      'spacy',
      'gradio',
      'ftfy',
      'transformers',
      'pandas'
    ],
    packages=setuptools.find_packages(),
    python_requires='>=3.10'
)
