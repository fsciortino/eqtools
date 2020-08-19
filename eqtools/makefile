# Usage:
# make           # generate eqtools shared-object library
# make clean     # delete previous versions of the eqtools shared-object library

.PHONY: all eqtools clean

flags="-fast"
fcompiler=intelem
#flags=
#fcompiler=gnu95


############

all: eqtools

eqtools : 
	@echo "Generating eqtools shared-object library"
	@echo "Compiler flags: " ${flags}
	f2py3 -c --compiler=intelem _tricub.pyf _tricub.c --opt=${flags}

clean : 
	@echo "Eliminating eqtools shared-object library"
	rm *.so

