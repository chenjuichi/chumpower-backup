using System;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading.Tasks;

class Program
{
    static async Task Main()
    {
        TcpListener server = new TcpListener(IPAddress.Any, 6400);
        server.Start();
        Console.WriteLine("C# TCP Server started...");

        while (true)
        {
            TcpClient client = await server.AcceptTcpClientAsync();
            _ = HandleClientAsync(client); // 開新 Task 處理客戶端
        }
    }

    static async Task HandleClientAsync(TcpClient client)
    {
        Console.WriteLine("Client connected.");
        try
        {
            using (NetworkStream stream = client.GetStream())
            {
                byte[] buffer = new byte[1024];

                while (true) // 允許持續接收多筆資料
                {
                    int bytesRead = await stream.ReadAsync(buffer, 0, buffer.Length);
                    if (bytesRead == 0) break; // 連線已關閉

                    string message = Encoding.UTF8.GetString(buffer, 0, bytesRead);
                    Console.WriteLine("Received from Node.js: " + message);

                    if (message.Trim().ToLower() == "exit")
                    {
                        Console.WriteLine("Client requested to close connection.");
                        break; // 結束與此客戶端的溝通
                    }

                    // 回傳確認訊息
                    byte[] response = Encoding.UTF8.GetBytes("ACK: " + message);
                    await stream.WriteAsync(response, 0, response.Length);
                }
            }
        }
        catch (Exception ex)
        {
            Console.WriteLine("Error: " + ex.Message);
        }
        finally
        {
            client.Close();
            Console.WriteLine("Client disconnected.");
        }
    }
}
