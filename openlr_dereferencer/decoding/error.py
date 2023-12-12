class LRDecodeError(Exception):
    "An error that happens through decoding location references"


class LRTimeoutError(Exception):
    "A timeout error that happens through decoding location references"


class LRFirstLRPNoCandidatesError(Exception):
    "An error that happens when no candidates are found for first lrp."


class LRLastLRPNoCandidatesError(Exception):
    "An error that happens when no candidates are found for last lrp."
