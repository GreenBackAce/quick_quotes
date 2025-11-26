import inspect
from pyannote.audio import Pipeline

print(inspect.signature(Pipeline.from_pretrained))
