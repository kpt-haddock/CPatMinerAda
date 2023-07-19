# CPatMinerAda

CPatMiner port for the Ada programming language.

CPatMiner is a graph-based mining approach for detecting repetitive fine-grained semantic code change patterns.

## Getting started

0. The tool requires Python 3.10+ to run. We have tested it only on Linux and Windows systems.
```
sudo apt install python3 python3-pip
```
2. Install the required dependencies:
    * Most dependencies of CPatMinerAda are easily installed from using the requirements.txt:
    ```shell script
    pip install -r requirements.txt
    ```
    * Libadalang (install using alire):
        * Install gnat and gprbuild
        ```
        sudo apt install gnat gprbuild
        ```
        * Download [alire](https://alire.ada.dev/)
        * Install alire following the [Getting Started](https://github.com/alire-project/alire/blob/master/doc/getting-started.md) instructions.
        * Create a dependencies folder and move into it, for example:
        ```shell script
        mkdir dependencies
        cd dependencies
        alr get libadalang
        ```
      * Build & Install
      ```
      cd libadalang_23.0.0_f27a5d00
      alr build
      sudo find . -type f,l -name "*.so" -exec cp "{}" /usr/local/lib \;
      cd python
      pip install .
      ```
3. Configure the settings file

### Installing alr

## Extracting Change Graphs From Commits
