import json
import os
import re
from shutil import copyfile
from typing import List, Dict
from collections import Counter

filename = "chapter2.txt"


def load_data_from_file(path=None) -> str:
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
        self.last_char_position = 0

    mapfile = "mapping.json"

    def write_map(self) -> None:
        """Write the current 'database' mapping to file."""
        with open(self.mapfile, 'w') as m:
            json.dump(self.mapping, m, indent=2)

    def load_map(self) -> Dict:
        """Load the 'database' mapping from file."""
        if not os.path.exists(self.mapfile):
            return dict()
        with open(self.mapfile, 'r') as m:
            return json.load(m)

    def _reset_char_position(self):
        self.last_char_position = 0

    def get_shard_ids(self):
        return sorted([key for key in self.mapping.keys() if '-' not in key])

    def get_replication_ids(self):
        return sorted([key for key in self.mapping.keys() if '-' in key])

    def build_shards(self, count: int, data: str = None) -> [str, None]:
        """Initialize our miniature databases from a clean mapfile. Cannot
        be called if there is an existing mapping -- must use add_shard() or
        remove_shard()."""
        if self.mapping != {}:
            return "Cannot build shard setup -- sharding already exists."

        spliced_data = self._generate_sharded_data(count, data)

        for num, d in enumerate(spliced_data):
            self._write_shard(num, d)

        self.write_map()

    def _write_shard_mapping(self, num: str, data: str, replication=False):
        """Write the requested data to the mapfile. The optional `replication`
        flag allows overriding the start and end information with the shard
        being replicated."""
        if replication:
            parent_shard = self.mapping.get(num[:num.index('-')])
            self.mapping.update(
                {
                    num: {
                        'start': parent_shard['start'],
                        'end': parent_shard['end']
                    }
                }
            )
        else:
            if int(num) == 0:
                # We reset it here in case we perform multiple write operations
                # within the same instantiation of the class. The char position
                # is used to power the index creation.
                self._reset_char_position()

            self.mapping.update(
                {
                    str(num): {
                        'start': (
                            self.last_char_position if
                            self.last_char_position == 0 else
                            self.last_char_position + 1
                        ),
                        'end': self.last_char_position + len(data)
                    }
                }
            )

            self.last_char_position += len(data)

    def _write_shard(self, num: int, data: str) -> None:
        """Write an individual database shard to disk and add it to the
        mapping."""
        if not os.path.exists("data"):
            os.mkdir("data")
        with open(f"data/{num}.txt", 'w') as s:
            s.write(data)
        self._write_shard_mapping(str(num), data)

    def _generate_sharded_data(self, count: int, data: str) -> List[str]:
        """Split the data into as many pieces as needed."""
        splicenum, rem = divmod(len(data), count)

        result = [data[splicenum * z:splicenum *
                       (z + 1)] for z in range(count)]
        # take care of any odd characters
        if rem > 0:
            result[-1] += data[-rem:]

        return result

    def load_data_from_shards(self) -> str:
        """Grab all the shards, pull all the data, and then concatenate it."""
        result = list()

        for db in self.get_shard_ids():
            with open(f'data/{db}.txt', 'r') as f:
                result.append(f.read())
        return ''.join(result)

    def add_shard(self) -> None:
        """Add a new shard to the existing pool and rebalance the data."""
        self.mapping = self.load_map()
        data = self.load_data_from_shards()
        keys = [int(z) for z in self.get_shard_ids()]
        keys.sort()
        # why 2? Because we have to compensate for zero indexing
        new_shard_num = max(keys) + 2

        spliced_data = self._generate_sharded_data(new_shard_num, data)

        for num, d in enumerate(spliced_data):
            self._write_shard(num, d)

        self.write_map()

        self.sync_replication()

    def remove_shard(self) -> None:
        """Loads the data from all shards, removes the extra 'database' file,
        and writes the new number of shards to disk.
        """
        self.mapping = self.load_map()
        keys = [int(z) for z in self.get_shard_ids()]
        keys.sort()
        # zero indexing removes 1 for us so nothing needs to be added
        new_shard_num = max(keys)

        data = self.load_data_from_shards()

        spliced_data = self._generate_sharded_data(new_shard_num, data)
        del self.mapping[str(new_shard_num)]
        for file in os.listdir(f'data'):
            if '-' not in file:
                os.remove(f'data/{file}')
        for num, d in enumerate(spliced_data):
            self._write_shard(num, d)

        self.write_map()
        self.sync_replication()

    def add_replication(self) -> None:
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
        d = {'src': [], 'rep': []}
        for key in self.mapping.keys():
            if '-' not in key:
                d['src'].append(key)
            else:
                d['rep'].append(int(key[key.index('-')+1:]))
        shard_level = max(d['rep']) if d['rep'] else 0

        for f in d['src']:
            x = f'{f}-{shard_level+1}.txt'
            f = f+'.txt'
            copyfile(f'data/{f}', f'data/{x}')
            self._write_shard_mapping(x[:x.index('.')], "", True)
        self.write_map()
        self.sync_replication()

    def remove_replication(self) -> None:
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
        d = {'src': [], 'rep': []}
        for key in self.mapping.keys():
            if '-' not in key:
                d['src'].append(key)
            else:
                d['rep'].append(int(key[key.index('-')+1:]))
        shard_level = max(d['rep']) if d['rep'] else 0
        if shard_level == 0:
            raise Exception("cannot remove primary shard")

        for f in d['src']:
            x = f'{f}-{shard_level}'
            del self.mapping[x]
            os.remove(f'data/{x}.txt')
        self.write_map()
        self.sync_replication()

    def sync_replication(self) -> None:
        """Verify that all replications are equal to their primaries and that
        any missing primaries are appropriately recreated from their
        replications."""

        mapping_keys = []
        files = []
        src = []
        max_file = 0
        for key in self.mapping.keys():
            if '-' not in key:
                src.append(key)
            else:
                max_file = int(key[key.index('-')+1:]) if int(key[key.index('-')+1:]) > max_file else max_file
            mapping_keys.append(key+'.txt')
        if not os.path.exists("data"):
            os.mkdir("data")
        for file in os.listdir('data/'):
            files.append(file)

        files.sort()
        mapping_keys.sort()

        for i in range(len(mapping_keys)):
            try:
                if files[i] != mapping_keys[i]:
                    rep_list = list(
                        filter(lambda x: x[:1] == mapping_keys[i][:1], files))
                    if rep_list[0] != mapping_keys[i]:
                        copyfile(f'data/{rep_list[0]}', f'data/{mapping_keys[i]}')
                        files.append(mapping_keys[i])
                        files.sort()
                    else:
                        for x in src:
                            for i in range(max_file):
                                v = f'{x}-{i}.txt'
                                copyfile(f'data/{x}.txt', f'data/{v}')
                                self._write_shard_mapping(v[:v.index('.')], "", True)
                        self.write_map()

            except IndexError:
                try:
                    rep_list = list(
                        filter(lambda x: x[:1] == mapping_keys[i][:1], files))
                    copyfile(f'data/{rep_list[0]}', f'data/{mapping_keys[i]}')
                    files.append(mapping_keys[i])
                except IndexError:
                    raise Exception(
                        "Critical integrity Error: All replications and primary lost for shard - "+mapping_keys[i][:1])
        for x in src:
            for i in range(max_file):
                v = f'{x}-{i}.txt'
                copyfile(f'data/{x}.txt', f'data/{v}')
                self._write_shard_mapping(v[:v.index('.')], "", True)
        self.write_map()


    def get_shard_data(self, shardnum=None) -> [str, Dict]:
        """Return information about a shard from the mapfile."""
        if not shardnum:
            return self.get_all_shard_data()
        data = self.mapping.get(shardnum)
        if not data:
            return f"Invalid shard ID. Valid shard IDs: {self.get_shard_ids()}"
        return f"Shard {shardnum}: {data}"

    def get_all_shard_data(self) -> Dict:
        """A helper function to view the mapping data."""
        return self.mapping


s = ShardHandler()
s.sync_replication()

s.build_shards(5, load_data_from_file())


s.add_shard()


s.remove_shard()


s.add_replication()
s.add_replication()


s.remove_replication()
s.add_shard()