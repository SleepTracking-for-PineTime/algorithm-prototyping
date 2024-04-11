SRCS = $(wildcard *.cpp)
OBJS = $(SRCS:.cpp=.o)
DEPS = $(SRCS:.cpp=.d)

SRCS += InfiniTime/src/components/sleep/SleepTracker.cpp

CFLAGS += -IInfiniTime/src
CFLAGS += -IInfiniTime/src/components/sleep/

main: $(OBJS)
	$(CXX) ${CFLAGS} $^ -o $@

%.o: %.cpp
	$(CXX) -std=c++20 ${CFLAGS} -MMD -MP -c $< -o $@

compile_commands.json:
	$(MAKE) clean
	bear -- $(MAKE)

.PHONY: clean compile_commands.json

clean:
	$(RM) $(OBJS) $(DEPS) main

-include $(DEPS)
