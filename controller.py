import os, json

filename = "chapter2.txt"

def load_data_from_file(path=None):
    with open(path if path else filename, 'r') as f:
        data = f.read()
    return data

class ShardHandler(object):
    """
    Take any text file and shard it into X number of files with
    Y number of replications.
    """
    def __init__(self):
        self.mapping = self.load_map()

    mapfile = "mapping.json"

    def write_map(self):
        """Write the current 'database' mapping to file."""
        with open(self.mapfile, 'w') as m:
            json.dump(self.mapping, m, indent=2)

    def load_map(self):
        """Load the 'database' mapping from file."""
        if not os.path.exists(self.mapfile):
            return dict()
        with open(self.mapfile, 'r') as m:
            return json.load(m)

    def build_shards(self, count, data=None):
        """Initialize our miniature databases from a clean mapfile. Cannot
        be called if there is an existing mapping -- must use add_shard() or
        remove_shard()."""
        if self.mapping != {}:
            return "Cannot build shard setup -- sharding already exists."

        spliced_data = self._generate_sharded_data(count, data)

        for num, d in enumerate(spliced_data):
            self._write_shard(num, d)

        self.write_map()

    def _write_shard(self, num, data):
        """Write an individual database shard to disk and add it to the
        mapping."""
        if not os.path.exists("data"):
            os.mkdir("data")
        with open(f"data/{num}.txt", 'w') as s:
            s.write(data)

        self.mapping.update(
            #mapping tells us where the data is and where to find it
            {
                str(num): {
                    'start': num * len(data),
                    'end': (num + 1) * len(data)
                }
            }
        )

        #doesn't need to return anything

    def _generate_sharded_data(self, count, data):
        """Split the data into as many pieces as needed."""
        splicenum, rem = divmod(len(data), count) #where we need to interact with the data and 
        #how to divide it up; first paramenter is how and the second is where to start with the 
        #leftover


        result = [
            data[
                splicenum * z: #basic string slicing
                splicenum * (z + 1)] #this breaks up the blocks starting with 0
                for z in range(count) # returns all of our data
            ]
        # take care of any odd characters
        if rem > 0:
            result[-1] += data[-rem:] #getting the left over information from the database
            #data is the original big blob of text and return the leftover characters in the index

        return result #returns how many segments and what's left over

    def load_data_from_shards(self):
        """Grab all the shards, pull all the data, and then concatenate it."""
        result = list()

        for db in self.mapping.keys():
            with open(f'data/{db}.txt', 'r') as f:
                result.append(f.read())
        return ''.join(result)

    def add_shard(self):
        """Add a new shard to the existing pool and rebalance the data."""
        #figuring out how many items we have at first and where to start to add new data
        self.mapping = self.load_map()
        data = self.load_data_from_shards()
        # why 2? Because we have to compensate for zero indexing
        keys = [int(z) for z in list(self.mapping.keys())] #to get in the right order of strings
        #string map and integer map is always annoying/it's always alphabetizing them
        keys.sort()
        new_shard_num = str(max(keys) + 2) #to help with 0 indexing

        spliced_data = self._generate_sharded_data(int(new_shard_num), data)
        #original data split into evenly divided segments and what is left over

        for num, d in enumerate(spliced_data):
            #enumerate means looping through our data and gives up the looped number we are on 
            #and the element for that loop
            #you can use this to write your file
            self._write_shard(num, d)

        self.write_map()
        #all the information is updated and written to disk with correct number of index's in it

    def remove_shard(self):
        """Loads the data from all shards, removes the extra 'database' file,
        and writes the new number of shards to disk.
        """
        self.mapping = self.load_map()
        data = self.load_data_from_shards()

        new_shard_num = str(int(max(list(self.mapping.keys))) + 2)

        spliced_data = self._generate_sharded_data(int(new_shard_num), data)

        for num, d in enumerate(spliced_data):
            self._write_shard(num, d)

        self.write_map()

    def add_replication(self):
        """Add a level of replication so that each shard has a backup. Label
        them with the following format:

        1.txt (shard 1, primary)
        1-1.txt (shard 1, replication 1)
        1-2.txt (shard 1, replication 2)
        2.txt (shard 2, primary)
        2-1.txt (shard 2, replication 1)
        ...etc.

        By default, there is no replication -- add_replication should be able
        to detect how many levels there are and appropriately add the next
        level.
        """
        pass

    def remove_replication(self):
        """Remove the highest replication level.

        If there are only primary files left, remove_replication should raise
        an exception stating that there is nothing left to remove.

        For example:

        1.txt (shard 1, primary)
        1-1.txt (shard 1, replication 1)
        1-2.txt (shard 1, replication 2)
        2.txt (shard 2, primary)
        etc...

        to:

        1.txt (shard 1, primary)
        1-1.txt (shard 1, replication 1)
        2.txt (shard 2, primary)
        etc...
        """
        pass

    def sync_replication(self):
        """Verify that all replications are equal to their primaries and that
         any missing primaries are appropriately recreated from their
         replications."""
        pass

    def get_shard_data(self, shardnum=None):
        """Return information about a shard from the mapfile."""
        if not shardnum:
            return self.get_all_shard_data()
        data = self.mapping.get(shardnum)
        if not data:
            return f"Invalid shard ID. Valid shard IDs: {self.mapping.keys()}"
        return f"Shard {shardnum}: {data}"

    def get_all_shard_data(self):
        """A helper function to view the mapping data."""
        return self.mapping


s = ShardHandler()

s.build_shards(5, load_data_from_file())

print(s.mapping.keys())

s.add_shard()

print(s.mapping.keys())
