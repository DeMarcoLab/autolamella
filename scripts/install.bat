CALL conda.bat create -n autolamella2 python=3.9 pip
CALL activate autolamella2
cd autolamella2
pip install -e .
python shortcut.py 