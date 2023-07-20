# CPatMinerAda

CPatMiner port for the Ada programming language.

CPatMiner is a graph-based mining approach for detecting repetitive fine-grained semantic code change patterns.

## Getting started (Linux instructions)

0. The tool requires Python 3.10+ to run. We have tested it only on Linux and Windows systems.
```
sudo apt install python3 python3-pip
```
1. Clone this repository
```shell script
git clone https://github.com/kpt-haddock/CPatMinerAda.git && cd CPatMinerAdacp
```
2. Install the required dependencies:
    * Most dependencies of CPatMinerAda are easily installed by using the requirements.txt:
    ```shell script
    pip3 install -r requirements.txt
    ```
    * GraphViz is required to generate PDF files for flow and change graphs:
    ```
    sudo apt install graphviz
    ```
    * Libadalang (install using alire):
        * Install gnat and gprbuild
        ```
        sudo apt install gnat gprbuild
        ```
        * Download [alire](https://alire.ada.dev/)
        * Install alire following the [Getting Started](https://github.com/alire-project/alire/blob/master/doc/getting-started.md) instructions.
        * Download, build, and install libadalang and its dependencies:
        ```shell script
        alr get libadalang
        ```
        ```shell script
        cd libadalang_23.0.0_f27a5d00
        ```
        Open the alire.toml file and add the following line below [[depends-on]]
        ```shell script
        gnat_native = "12.2.1"
        ```
        Build libadalang:
        ```shell script
        alr build
        ```
        Install the shared object libraries:
        ```shell script
        sudo find . -type f,l -name "*.so" -exec cp "{}" /usr/local/lib \;
        ```
        Add /usr/local/lib to your path environment:
        ```shell script
        sudo vim /etc/environment
        ```
        Configure dynamic linker run-time bindings:
        ```shell script
        sudo ldconfig
        ```
        ```
        cd python
        pip3 install .
        ```
        Now run test_libadalang_installation.py to verify that the libadalang installation has been successful:
        ```shell script
        python3 test_libadalang_installation.py
        ```
3. Configure the settings file

### Installing alr

## How to use
You can run any step of the pipeline by using the following command:
```
python3 src/main.py <mode> <args>
```
CPatMinerAda currently supports four operation modes:
1. `afg` — build a program dependence graph from the Ada source.
   Arguments
   * `-i` — path to the source file.
   * `-o` — path to the output file; two files are created, a DOT graph file and a graphviz-generated PDF file.
   * `--no-closure` — **(optional)** no closure will be built for the graph.
   * `--show-deps` — **(optional)** edges with type dep will be present in the graph, indicating the dependence of the vertices on each other.
   * `--hide-op-kinds` — **(optional)** hide operation types.
   * `--show-data-keys` — **(optional)** show variable IDs.
   Typical use:
   ```
   python3 src/main.py afg -i src/examples/example.adb -o images/afg.dot
   ```
2. `cg` — build a change graph from two source files (before and after changes).
   Arguments:
   * `-s` — path to the source file before changes.
   * `-d` — path to the source file after changes.
   * `-o` — path to the output file; two files are created, a DOT graph file and a graphviz-generated PDF file.
   Typical use:
   ```
   python3 src/main.py cg -s src/examples/0_old.adb -d src/examples/0_new.adb -o images/cg.dot
   ```
3. `collect-cgs` — mine change graphs from local repositories.
   All general settings for this mode are located in the configuration JSON file (see part 3 of **Getting started**.
   Use:
   ```
   python3 src/main.py collect-cgs
   ```
4. `patterns` — search for patterns in the generated change graphs.
   All general settings for this mode are located in the configuration JSON file (see part 3 of **Getting started**.
   
   Use:
   ```
   python3 src/main.py patterns
   ```
