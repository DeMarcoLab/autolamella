# Automatic FIBSEM lamella milling


## Running the tests
To run the test suite:
```
pytest
```

Ignore the warning about pytest not recognising `pytest.mark.mpl_image_compare`

To generate new baseline test image results:
```
pytest --mpl-generate-path=tests\baseline
```