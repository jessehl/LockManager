#include <vector>
#include <thread>
#include <string>
#include "DDserver.h"
#include "crow.h"
#include <iostream>

namespace DoubleD
{
    std::vector<Lock> DDserver::m_lockVector;
    boost::mutex DDserver::m_storageMutex;
    bool DDserver::isRunning = true;

    DDserver::DDserver()
    {}

    void DDserver::m_startup(const unsigned int portNum, const unsigned int numOfThreads) {

        crow::SimpleApp app;
        CROW_ROUTE(app, "/")([]() { return "Welcome to DoubleDutch"; });

        // need to figure out how to return actual json
        CROW_ROUTE(app, "/status")
            ([&] {
            std::string tempString;
            for (long unsigned int i = 0; i < DDserver::m_lockVector.size(); i++) {
                tempString = tempString + "LOCK= " + DDserver::m_lockVector[i].m_getName() +
                    "\n" + "USER_ID= " + DDserver::m_lockVector[i].m_getUser_id() +
                    "\n\n";
            }
            return tempString;
                });

        CROW_ROUTE(app, "/getLock")
            ([](const crow::request& req)
                {
                    std::string lockName;
                    double lifetime;
                    double timeout;

                    if (req.url_params.get("lockname") == nullptr)
                    {
                        std::string ep = "false";
                        return ep;
                    }

                    else
                    {
                        lockName = req.url_params.get("lockname");
                    }

                    if (req.url_params.get("lifetime") != nullptr)
                    {
                        lifetime = boost::lexical_cast<double>(req.url_params.get("lifetime"));
                    }

                    else
                    {
                        lifetime = 30.0f;
                    }

                    if (req.url_params.get("timeout") != nullptr)
                    {
                        timeout = boost::lexical_cast<double>(req.url_params.get("timeout"));
                    }

                    else
                    {
                        timeout = 0.0f;
                    }


                    if (DDserver::m_reqTimedout(timeout, lockName))
                    {
                        std::string ep = "false";
                        return ep;
                    }

                    else
                    {
                        Lock tempLock(lockName, lifetime);
                        DDserver::m_lockVector.push_back(tempLock);
                        DDserver::m_storageMutex.unlock();
                        return tempLock.m_getUser_id();
                    }

                });

        // Releasing the lock
        CROW_ROUTE(app, "/releaseLock/<string>/<string>")
            ([&](std::string lockName, std::string user_id) {
            DDserver::m_storageMutex.lock();
            for (long unsigned int i = 0; i < DDserver::m_lockVector.size(); i++) {
                if (lockName == DDserver::m_lockVector[i].m_getName() &&
                    user_id == DDserver::m_lockVector[i].m_getUser_id()) {
                    DDserver::m_lockVector.erase(DDserver::m_lockVector.begin() + i);
                    DDserver::m_lockVector.shrink_to_fit();
                    DDserver::m_storageMutex.unlock();
                    return "released";
                }
            }
            DDserver::m_storageMutex.unlock();
            return "false";
                });

        app.port(portNum).concurrency(numOfThreads).run();
        DDserver::isRunning = false;
    }

    void DDserver::m_checkLifetimes()
    {
        while (DDserver::isRunning)
        {
            std::this_thread::sleep_for(std::chrono::milliseconds(500));
            DDserver::m_storageMutex.lock();
            for (unsigned int i = 0; i < DDserver::m_lockVector.size(); i++)
            {
                if (DDserver::m_lockVector[i].m_expired())
                {
                    DDserver::m_lockVector.erase(DDserver::m_lockVector.begin() + i);
                    DDserver::m_lockVector.shrink_to_fit();
                }
            }
            DDserver::m_storageMutex.unlock();
        }
    }

    bool DDserver::m_reqTimedout(unsigned int timeout, std::string lockName)
    {
        auto startTime = std::chrono::high_resolution_clock::now();
        auto currentTime = std::chrono::high_resolution_clock::now();
        std::chrono::duration<double> difference = currentTime - startTime;
        while (difference.count() <= timeout)
        {
            currentTime = std::chrono::high_resolution_clock::now();
            difference = currentTime - startTime;

            DDserver::m_storageMutex.lock();
            if (DDserver::m_lockVector.size() == 0)
            {
                return false;
            }

            for (long unsigned int i = 0; i < DDserver::m_lockVector.size(); i++)
            {
                if (lockName == DDserver::m_lockVector[i].m_getName())
                {
                    break;
                }

                else if (i == DDserver::m_lockVector.size() - 1)
                {
                    return false;
                }
            }
            DDserver::m_storageMutex.unlock();
            std::this_thread::sleep_for(std::chrono::milliseconds(500));
        }
        return true;
    }
}
