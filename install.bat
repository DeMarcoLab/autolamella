CALL conda.bat create -n autolamella python=3.9 pip
CALL activate autolamella
pip install -e .
cd ..
cd fibsem
pip install -e .