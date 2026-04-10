export default function PaymentHistoryTable({ payments }: any) {
  return (
    <table className="w-full bg-gray-900 rounded-xl">
      <thead>
        <tr className="text-gray-400">
          <th className="p-4">Amount</th>
          <th className="p-4">Date</th>
          <th className="p-4">Status</th>
        </tr>
      </thead>
      <tbody>
        {payments.map((p: any) => (
          <tr key={p.id} className="border-t border-gray-800">
            <td className="p-4">₹{p.amount}</td>
            <td className="p-4">{p.created_at}</td>
            <td className="p-4">{p.status}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}