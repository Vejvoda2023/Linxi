class RingBuffer:
    def __init__(self, size):
        self.size = size
        self.data = []
        self.full = False
        self.cur = 0

    def append(self, x):
        if self.full:
            self.data[self.cur] = x
            self.cur = (self.cur + 1) % self.size
        else:
            self.data.append(x)
            if len(self.data) == self.size:
                self.full = True

    def get_all(self):
        return [self.data[(i + self.cur) % self.size] for i in range(len(self.data))]

    def clear(self):
        self.data = []
        self.full = False
        self.cur = 0
