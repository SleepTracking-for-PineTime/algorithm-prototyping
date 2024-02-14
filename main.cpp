#include "SleepTracker.h"

#include <iostream>
#include <fstream>

float currtime = 0;

void callback(uint8_t state) {
    std::cout << currtime << " " << (int)state << std::endl;
}

int main(int argc, char *argv[]) {
    if (argc < 2) {
        std::cerr << "Usage: " << argv[0] << " [INFILE]" << std::endl;
        std::cerr << "Where [INFILE] is a whitespace-delimited file where each row holds:" << std::endl;
        std::cerr << "  TIME X Y Z TRUTH" << std::endl;
        std::cerr << "The input sample rate must be 10 Hz, with one row per sample." << std::endl;
        std::cerr << "Output is one line for each change in state in format:" << std::endl;
        std::cerr << "  TIME STATE" << std::endl;
        std::cerr << "Where [STATE] is 0 or 1 for wake or sleep." << std::endl;
        exit(1);
    }

    std::ifstream infile(argv[1]);
    if (!infile.is_open()) {
        std::cerr << "Unable to open '" << argv[1] << "'" << std::endl;
        exit(1);
    }

    auto tracker = Pinetime::SleepTracker::VanHeesSleepTracker(callback);

    float t, x, y, z, truth;
    while (infile >> t >> x >> y >> z >> truth) {
        currtime = t;
        tracker.UpdateAccel(x, y, z);
    }

    return 0;
}
