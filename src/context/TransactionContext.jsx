import React, { createContext, useState, useEffect } from 'react';

export const TransactionContext = createContext();

export const TransactionProvider = ({ children }) => {
    const [user, setUser] = useState(null);
    const [transactions, setTransactions] = useState([]);
    const [debts, setDebts] = useState([]);
    const [vpa, setVpa] = useState(localStorage.getItem('userVpa') || '');
    const [loading, setLoading] = useState(true);
    const [theme, setTheme] = useState(localStorage.getItem('theme') || 'light');
    const [nudges, setNudges] = useState([]);
    const [appUsers, setAppUsers] = useState([]);

    // Update theme class on body
    useEffect(() => {
        if (theme === 'dark') {
            document.documentElement.classList.add('dark');
        } else {
            document.documentElement.classList.remove('dark');
        }
        localStorage.setItem('theme', theme);
    }, [theme]);

    // Check auth status on load
    useEffect(() => {
        checkAuth();
    }, []);

    // Fetch data when user changes
    useEffect(() => {
        if (user) {
            fetchTransactions();
            fetchDebts();
            fetchNudges();
            fetchAppUsers();
        } else {
            setTransactions([]);
            setDebts([]);
            setNudges([]);
            setAppUsers([]);
        }
    }, [user]);

    const checkAuth = async () => {
        try {
            const res = await fetch('/api/check_auth');
            const data = await res.json();
            if (data.isAuthenticated) {
                setUser({ username: data.username });
            }
        } catch (err) {
            console.error("Auth check failed", err);
        } finally {
            setLoading(false);
        }
    };

    const login = async (email, password) => {
        try {
            const res = await fetch('/api/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password })
            });
            const data = await res.json();
            if (res.ok) {
                setUser({ username: data.username, email: data.email });
                return { success: true };
            }
            return { success: false, error: data.error || 'Login failed' };
        } catch (err) {
            return { success: false, error: 'Connection error' };
        }
    };

    const register = async (username, email, password, otp) => {
        try {
            const res = await fetch('/api/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, email, password, otp })
            });
            const data = await res.json();
            if (res.ok) {
                return { success: true };
            }
            return { success: false, error: data.error || 'Registration failed' };
        } catch (err) {
            return { success: false, error: 'Connection error' };
        }
    };

    const logout = async () => {
        await fetch('/api/logout', { method: 'POST' });
        setUser(null);
    };

    const deleteAccount = async () => {
        try {
            const res = await fetch('/api/delete-account', { method: 'DELETE' });
            if (res.ok) {
                setUser(null);
                return { success: true };
            }
            return { success: false };
        } catch (err) {
            return { success: false };
        }
    };

    const sendOtp = async (email, type) => {
        try {
            const res = await fetch('/api/send-otp', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, type })
            });
            const data = await res.json();
            return { success: res.ok, error: data.error };
        } catch (err) {
            return { success: false, error: 'Connection error' };
        }
    };

    const resetPassword = async (email, otp, newPassword) => {
        try {
            const res = await fetch('/api/reset-password', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, otp, new_password: newPassword })
            });
            const data = await res.json();
            return { success: res.ok, error: data.error };
        } catch (err) {
            return { success: false, error: 'Connection error' };
        }
    };

    const fetchTransactions = async () => {
        try {
            const res = await fetch('/api/transactions');
            if (res.ok) {
                const data = await res.json();
                setTransactions(data);
            }
        } catch (err) {
            console.error("Failed to fetch transactions", err);
        }
    };

    const fetchDebts = async () => {
        try {
            const res = await fetch('/api/debts');
            if (res.ok) {
                const data = await res.json();
                setDebts(data);
            }
        } catch (err) {
            console.error("Failed to fetch debts", err);
        }
    };

    const addTransaction = async (transaction) => {
        try {
            const res = await fetch('/api/transactions', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(transaction)
            });
            if (res.ok) {
                fetchTransactions(); // Refresh list
            }
        } catch (err) {
            console.error("Failed to add transaction", err);
        }
    };

    const deleteTransaction = async (id) => {
        try {
            const res = await fetch(`/api/transactions/${id}`, { method: 'DELETE' });
            if (res.ok) {
                setTransactions(prev => prev.filter(t => t.id !== id));
            }
        } catch (err) {
            console.error("Failed to delete transaction", err);
        }
    };

    const addDebt = async (debt) => {
        try {
            const res = await fetch('/api/debts', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(debt)
            });
            if (res.ok) {
                fetchDebts(); // Refresh list
            }
        } catch (err) {
            console.error("Failed to add debt", err);
        }
    };

    const deleteDebt = async (id) => {
        try {
            const res = await fetch(`/api/debts/${id}`, { method: 'DELETE' });
            if (res.ok) {
                setDebts(prev => prev.filter(d => d.id !== id));
            }
        } catch (err) {
            console.error("Failed to delete debt", err);
        }
    };

    const clearPersonDebts = async (name) => {
        try {
            const res = await fetch(`/api/debts/clear/${encodeURIComponent(name)}`, { method: 'DELETE' });
            if (res.ok) {
                setDebts(prev => prev.filter(d => d.name.toLowerCase() !== name.toLowerCase()));
            }
        } catch (err) {
            console.error("Failed to clear person debts", err);
        }
    };

    const addBulkItems = async (items) => {
        for (const item of items) {
            if (item.is_debt) {
                // 1. Add to Ledger
                await addDebt({
                    amount: item.amount,
                    name: item.name,
                    type: item.type,
                    description: item.description,
                    date: new Date().toISOString()
                });

                // 2. Add to Dashboard (Sync)
                // If I LENT, it's an Expense. If I BORROWED/RECEIVED, it's Income.
                const syncType = item.type === 'lent' ? 'expense' : 'income';
                await addTransaction({
                    amount: item.amount,
                    description: `${item.type === 'lent' ? 'Lent to' : 'Received from'} ${item.name}`,
                    type: syncType,
                    category: 'Ledger-Linked',
                    date: new Date().toISOString()
                });
            } else {
                await addTransaction({
                    amount: item.amount,
                    description: item.description,
                    type: item.type,
                    category: item.category || 'General',
                    date: new Date().toISOString()
                });
            }
        }
    };

    // Calculate net balance per person
    const getPersonBalance = (personName) => {
        return debts
            .filter(d => d.name.toLowerCase() === personName.toLowerCase())
            .reduce((total, debt) => {
                return total + (debt.type === 'lent' ? debt.amount : -debt.amount);
            }, 0);
    };

    // Get unique people with their balances
    const getPeopleBalances = () => {
        const peopleMap = {};
        debts.forEach(debt => {
            const name = debt.name;
            if (!peopleMap[name]) {
                peopleMap[name] = { name, balance: 0, transactions: [] };
            }
            const amount = debt.type === 'lent' ? debt.amount : -debt.amount;
            peopleMap[name].balance += amount;
            peopleMap[name].transactions.push({ ...debt, netAmount: amount });
        });
        return Object.values(peopleMap);
    };

    // --- New Social Methods ---
    const fetchAppUsers = async () => {
        try {
            const res = await fetch('/api/users');
            if (res.ok) {
                const data = await res.json();
                setAppUsers(data);
            }
        } catch (err) {
            console.error("Failed to fetch users", err);
        }
    };

    const fetchNudges = async () => {
        try {
            const res = await fetch('/api/nudges');
            if (res.ok) {
                const data = await res.json();
                setNudges(data);
            }
        } catch (err) {
            console.error("Failed to fetch nudges", err);
        }
    };

    const sendNudge = async (receiverId, amount, message) => {
        try {
            const res = await fetch('/api/nudges', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ receiver_id: receiverId, amount, message })
            });
            return res.ok;
        } catch (err) {
            console.error("Failed to send nudge", err);
            return false;
        }
    };

    const markNudgeRead = async (id) => {
        try {
            await fetch(`/api/nudges/read/${id}`, { method: 'POST' });
            setNudges(prev => prev.filter(n => n.id !== id));
        } catch (err) {
            console.error("Failed to mark nudge read", err);
        }
    };

    const sendMessage = async (receiverId, content) => {
        try {
            const res = await fetch('/api/messages', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ receiver_id: receiverId, content })
            });
            if (res.ok) {
                return await res.json();
            }
            return null;
        } catch (err) {
            console.error("Failed to send message", err);
            return null;
        }
    };

    const getMessages = async (friendId) => {
        try {
            const res = await fetch(`/api/messages/${friendId}`);
            if (res.ok) {
                return await res.json();
            }
            return [];
        } catch (err) {
            console.error("Failed to fetch messages", err);
            return [];
        }
    };

    return (
        <TransactionContext.Provider value={{
            user,
            loading,
            login,
            register,
            logout,
            deleteAccount,
            sendOtp,
            resetPassword,
            transactions,
            addTransaction,
            deleteTransaction,
            debts,
            addDebt,
            deleteDebt,
            addBulkItems,
            vpa,
            theme,
            toggleTheme: () => setTheme(prev => prev === 'light' ? 'dark' : 'light'),
            updateVpa: (newVpa) => {
                setVpa(newVpa);
                localStorage.setItem('userVpa', newVpa);
            },
            getPersonBalance,
            getPeopleBalances,
            clearPersonDebts,
            appUsers,
            nudges,
            fetchNudges,
            sendNudge,
            markNudgeRead,
            sendMessage,
            getMessages
        }}>
            {children}
        </TransactionContext.Provider>
    );
};
