
import queue


class FOV:
    def __init__(self, pos, index, path, metadata, properties):
        self.pos = pos #stage position
        self.index = index #unique index
        self.metadata = metadata #dict with metadata
        self.properties = properties #dict to store data required for experiment
        self.light_mask = None
        self.path = path # folder with experiment
        self.stim_params = {} #dict with the parameters the stimlator will unpack in the segment method
        self.stim_mask_queue = queue.Queue()
        self.tracks_queue = queue.Queue()
        self.start_time = None
        self.mda_sequence = None #mda sequence object used for timing
        self.tracks = None #tracks dataframe
        self.linker = None # Linker object that will be stored from trackpy


