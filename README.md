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
    pip install -r requirements.txt
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
        ```shell script
        
        ```
      * Build & Install
      ```
      cd libadalang_23.0.0_f27a5d00
      alr build
      sudo find . -type f,l -name "*.so" -exec cp "{}" /usr/local/lib \;
      cd python
      pip install .
      ```
      * Add /usr/local/lib to your PATH environment variable
      * Reload your environment
      ```
      sudo ldconfig
      ```
3. Configure the settings file

### Installing alr

## Extracting Change Graphs From Commits
