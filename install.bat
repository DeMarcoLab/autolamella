CALL conda.bat create -n autolamella python=3.9 pip
CALL activate autolamella
cd ..
cd fibsem
pip install -e .
cd ..
cd autolamella
pip install -e .