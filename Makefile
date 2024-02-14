SRCS = $(wildcard *.cpp)
OBJS = $(SRCS:.cpp=.o)
DEPS = $(SRCS:.cpp=.d)

CFLAGS += -IInfiniTime/src

main: $(OBJS)
	$(CXX) ${CFLAGS} $^ -o $@

%.o: %.cpp
	$(CXX) ${CFLAGS} -MMD -MP -c $< -o $@

compile_commands.json:
	$(MAKE) clean
	bear -- $(MAKE)

.PHONY: clean compile_commands.json

clean:
	$(RM) $(OBJS) $(DEPS) main

-include $(DEPS)